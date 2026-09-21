"""Proof-weighted skill scoring — the v2 change to the match score.

A skill written in a CV is only a *claim*. It counts fully only once it is
proven:

    proof level      how it is earned                               weight
    claimed          only written in the CV / profile               0.30
    quiz             passed the skill quiz (valid 180 days)          0.85
    hr_confirmed     an employer ticked "terbukti" after interview   1.00

Worked example (job needs Excel, Customer Service, Admin):
    A claims all three          -> (0.3 + 0.3 + 0.3) / 3 = 0.30
    B passed Excel + CS quizzes -> (0.85 + 0.85 + 0.3) / 3 = 0.67
So stuffing keywords into a CV no longer beats a candidate with proof.

Required skills weigh 80% and nice-to-have skills 20% of the skill part.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

PROOF_WEIGHTS: dict[str, float] = {"claimed": 0.30, "quiz": 0.85, "hr_confirmed": 1.0}
QUIZ_VALID_DAYS = 180
_REQUIRED_SHARE = 0.8

# Education ladder used for `education_min` comparisons.
_EDU_RANK = {"SMA": 0, "SMK": 0, "D3": 1, "D4": 2, "S1": 2, "S2": 3, "S3": 4}


def skill_key(name: str) -> str:
    """Canonical skill key — same normalisation the matcher uses."""
    from backend.app.services.matching.matcher import _normalize_skill

    return _normalize_skill(name)


def _get(skill, attr: str, default=None):
    if isinstance(skill, dict):
        return skill.get(attr, default)
    return getattr(skill, attr, default)


def effective_proof(skill, today: date | None = None) -> str:
    """Proof level after expiry: a quiz badge older than 180 days is a claim again."""
    level = _get(skill, "proof_level", "claimed") or "claimed"
    if level == "quiz":
        raw = _get(skill, "proof_date")
        try:
            earned = date.fromisoformat(str(raw)[:10])
        except (TypeError, ValueError):
            return "claimed"
        today = today or datetime.now(UTC).date()
        if (today - earned).days > QUIZ_VALID_DAYS:
            return "claimed"
    return level if level in PROOF_WEIGHTS else "claimed"


def proof_map(skills) -> dict[str, str]:
    """canonical skill key -> strongest effective proof level held."""
    out: dict[str, str] = {}
    for sk in skills or []:
        name = _get(sk, "name")
        if not name:
            continue
        key = skill_key(name)
        level = effective_proof(sk)
        if PROOF_WEIGHTS[level] > PROOF_WEIGHTS.get(out.get(key, ""), -1.0):
            out[key] = level
    return out


def _coverage(held: dict[str, str], wanted: list[str]) -> float | None:
    keys = [skill_key(w) for w in wanted if w]
    if not keys:
        return None
    return sum(PROOF_WEIGHTS[held[k]] if k in held else 0.0 for k in keys) / len(keys)


def proven_skill_score(skills, required: list[str], nice_to_have: list[str] | None = None) -> float:
    """Skill part of the match score in [0, 1], weighted by proof level.

    A posting with no skills listed carries no signal: neutral 0.5, the same
    rule the previous keyword-overlap score used.
    """
    held = proof_map(skills)
    req = _coverage(held, required or [])
    nice = _coverage(held, nice_to_have or [])
    if req is None and nice is None:
        return 0.5
    if nice is None:
        return req  # type: ignore[return-value]
    if req is None:
        return nice
    return _REQUIRED_SHARE * req + (1 - _REQUIRED_SHARE) * nice


def skill_proof_view(skills, required: list[str]) -> list[dict]:
    """Per required skill: {name, status} with status claimed/quiz/hr_confirmed/missing."""
    held = proof_map(skills)
    return [{"name": r, "status": held.get(skill_key(r), "missing")} for r in required or [] if r]


def skill_snapshot(skills) -> list[dict]:
    """[{name, proof_level}] stored on an application at apply time."""
    return [
        {"name": _get(sk, "name"), "proof_level": effective_proof(sk)}
        for sk in skills or []
        if _get(sk, "name")
    ]


def education_fit(education, education_min: str | None) -> float:
    """1.0 if the seeker's highest degree meets the job minimum, 0.5 if one
    level short, 0.0 otherwise or when no education is listed."""
    # SMA/SMK is rank 0 — the floor. A job sitting there has stated no
    # requirement, so nobody can fail it, including a seeker whose CV never
    # parsed an education entry. Education only discriminates once an employer
    # deliberately raises the bar above the floor.
    need = _EDU_RANK.get(str(getattr(education_min, "value", education_min) or "SMA").upper(), 0)
    if need <= 0:
        return 1.0

    ranks = []
    for e in education or []:
        degree = str(_get(e, "degree", "") or "").upper()
        degree = getattr(_get(e, "degree"), "value", degree) or degree
        if str(degree).upper() in _EDU_RANK:
            ranks.append(_EDU_RANK[str(degree).upper()])
    if not ranks:
        return 0.0
    best = max(ranks)
    if best >= need:
        return 1.0
    return 0.5 if best == need - 1 else 0.0


def carry_proof(new_skills: list, old_skills: list) -> list:
    """Keep earned proof when a profile's skill list is replaced.

    Clients can never set a proof level (the API skill input has no such
    field); proof is only earned via quiz or HR confirmation. So when a
    profile edit or CV re-upload replaces the skill list, copy each skill's
    existing proof over, and keep proven skills the new list dropped.
    """
    old_by_key = {}
    for sk in old_skills or []:
        if effective_proof(sk) != "claimed" or _get(sk, "proof_level") == "hr_confirmed":
            old_by_key[skill_key(_get(sk, "name", ""))] = sk
    seen = set()
    for sk in new_skills:
        key = skill_key(sk.name)
        seen.add(key)
        prev = old_by_key.get(key)
        if prev is not None:
            sk.proof_level = _get(prev, "proof_level", "claimed")
            sk.proof_date = _get(prev, "proof_date")
    kept = [sk for key, sk in old_by_key.items() if key not in seen]
    return list(new_skills) + kept
