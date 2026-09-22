"""Re-embed jobs and seekers whose vectors were produced by a different model.

Why this exists
---------------
`matcher.py` deliberately refuses to compare vectors across embedding models:

    job_vec = j.embedding if j.embedding_model == settings.gemini_embed_model else []

That is the right call — cosine similarity between two different models' vector
spaces is meaningless, and a plausible-looking wrong number is worse than none.
But it means that the moment `GEMINI_EMBED_MODEL` changes, every row still
tagged with the old model silently scores 0 on the cosine term, which is **45%
of the total match score**, until something happens to re-save that row.

So changing `GEMINI_EMBED_MODEL` is a migration, not a config tweak. Run this
straight after, against the same DATABASE_URL the app uses:

    cd backend && python -m scripts.reembed            # re-embed stale rows
    cd backend && python -m scripts.reembed --dry-run  # just count them
    cd backend && python -m scripts.reembed --all      # force every row

Safe to re-run: rows already on the current model are skipped, and a row whose
embed call fails is left as it was rather than written with a junk vector
(`embed_job` / `embed_seeker` swallow EmbeddingUnavailableError for exactly
this reason). Re-run it until "stale remaining" reaches 0.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config.settings import settings
from backend.app.db.postgres_store import get_repositories
from backend.app.services.matching.matcher import SemanticMatcher

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("reembed")

# Gemini's free tier allows a limited number of embed calls per minute, and a
# burst of failures would leave rows unembedded. Pause briefly between writes.
_PAUSE_S = 0.2


async def _reembed(kind: str, repo, embed, target: str, force: bool, dry_run: bool) -> int:
    rows = await repo.list()
    stale = [r for r in rows if force or (r.embedding_model or "") != target]
    if not stale:
        logger.info("[%s] %d rows, all already on %s", kind, len(rows), target)
        return 0

    logger.info("[%s] %d of %d rows need re-embedding", kind, len(stale), len(rows))
    if dry_run:
        by_model: dict[str, int] = {}
        for r in stale:
            by_model[r.embedding_model or "(none)"] = by_model.get(r.embedding_model or "(none)", 0) + 1
        for model, n in sorted(by_model.items(), key=lambda kv: -kv[1]):
            logger.info("    %-32s %d", model, n)
        return len(stale)

    done = 0
    for row in stale:
        await embed(row)
        # embed_* leaves embedding_model untouched when the call failed, so this
        # check is what keeps a failed row out of the "done" count — and out of
        # the database with a stale vector newly labelled as current.
        if (row.embedding_model or "") == target:
            await repo.upsert(row)
            done += 1
        else:
            logger.warning("    %s %s could not be embedded — left unchanged", kind, row.id)
        await asyncio.sleep(_PAUSE_S)
    logger.info("[%s] re-embedded %d, stale remaining %d", kind, done, len(stale) - done)
    return len(stale) - done


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="count stale rows, change nothing")
    parser.add_argument("--all", action="store_true", dest="force",
                        help="re-embed every row, not just those on another model")
    args = parser.parse_args()

    target = settings.gemini_embed_model
    logger.info("Target embedding model: %s (%d-dim)", target, settings.gemini_embed_dim)
    if not settings.gemini_api_key and not settings.vertex_ai_project and not args.dry_run:
        logger.error(
            "No GEMINI_API_KEY / VERTEX_AI_PROJECT configured. Without one the embedder "
            "falls back to the deterministic HashEmbedder, which would overwrite real "
            "vectors with hashes. Refusing to run."
        )
        return 2

    repos = get_repositories()
    matcher = SemanticMatcher()
    remaining = await _reembed("jobs", repos.jobs, matcher.embed_job, target, args.force, args.dry_run)
    remaining += await _reembed("seekers", repos.seekers, matcher.embed_seeker, target,
                                args.force, args.dry_run)

    if args.dry_run:
        logger.info("Dry run — nothing written. %d rows would be re-embedded.", remaining)
        return 0
    if remaining:
        logger.warning("%d rows still stale — re-run once the embedder recovers.", remaining)
        return 1
    logger.info("All rows are on %s.", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
