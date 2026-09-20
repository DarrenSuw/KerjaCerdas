"""v2 proof-weighted scoring, education fit, redaction and proof integrity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.db.schemas import Education, JobPosting, SeekerProfile, Skill
from backend.app.services.matching.evidence import (
    carry_proof,
    education_fit,
    effective_proof,
    proven_skill_score,
    skill_proof_view,
)
from backend.app.services.matching.matcher import _hybrid_score, score_pair
from backend.app.services.privacy.redact import redact_llm_input, redact_text

# UTC, because effective_proof() ages a badge against datetime.now(UTC).date().
# Using the local date made this suite fail for the ~7h each day when WIB has
# rolled over but UTC has not: a "181 day old" badge is only 180 days old in
# UTC and still counts as proven.
TODAY = datetime.now(UTC).date().isoformat()


class TestProofWeights:
    def test_worked_example_from_the_docs(self) -> None:
        required = ["Excel", "Customer Service", "Administrasi"]
        claimer = [Skill(name=s) for s in required]
        prover = [
            Skill(name="Excel", proof_level="quiz", proof_date=TODAY),
            Skill(name="Customer Service", proof_level="quiz", proof_date=TODAY),
            Skill(name="Administrasi"),
        ]
        assert round(proven_skill_score(claimer, required), 2) == 0.30
        assert round(proven_skill_score(prover, required), 2) == 0.67

    def test_keyword_stuffing_loses_to_proof(self) -> None:
        required = ["Excel", "Kasir"]
        stuffed = [Skill(name=n) for n in ["Excel", "Kasir", "SQL", "Python", "Sales", "Komunikasi"]]
        proven = [Skill(name="Excel", proof_level="quiz", proof_date=TODAY)]
        assert proven_skill_score(proven, required) > proven_skill_score(stuffed, required)

    def test_hr_confirmation_is_the_strongest_proof(self) -> None:
        hr = [Skill(name="Excel", proof_level="hr_confirmed")]
        quiz = [Skill(name="Excel", proof_level="quiz", proof_date=TODAY)]
        assert proven_skill_score(hr, ["Excel"]) == 1.0 > proven_skill_score(quiz, ["Excel"])

    def test_quiz_badge_expires_after_180_days(self) -> None:
        old = (datetime.now(UTC).date() - timedelta(days=181)).isoformat()
        assert effective_proof(Skill(name="Excel", proof_level="quiz", proof_date=old)) == "claimed"
        assert effective_proof(Skill(name="Excel", proof_level="quiz", proof_date=TODAY)) == "quiz"

    def test_aliases_count_as_the_same_skill(self) -> None:
        proven = [Skill(name="Microsoft Excel", proof_level="quiz", proof_date=TODAY)]
        assert skill_proof_view(proven, ["Excel"]) == [{"name": "Excel", "status": "quiz"}]

    def test_posting_without_skills_is_neutral(self) -> None:
        assert proven_skill_score([Skill(name="Excel")], []) == 0.5


class TestEducationFit:
    def test_meets_below_and_none(self) -> None:
        s1 = [Education(institution="UI", degree="S1", major="x", graduation_year=2024)]
        d3 = [Education(institution="PNJ", degree="D3", major="x", graduation_year=2024)]
        assert education_fit(s1, "S1") == 1.0
        assert education_fit(d3, "D4") == 0.5
        assert education_fit([], "D3") == 0.0  # a real bar, nothing evidenced

    def test_no_stated_requirement_penalises_nobody(self) -> None:
        """SMA/SMK is the floor: a job sitting there has stated no requirement,
        so there is nothing for any candidate to fail — including one whose CV
        never parsed an education entry. Education only discriminates once an
        employer deliberately raises the bar."""
        sma = [Education(institution="SMKN 1", degree="SMA", major="x", graduation_year=2024)]
        assert education_fit(sma, "SMA") == 1.0
        assert education_fit([], "SMA") == 1.0
        assert education_fit([], None) == 1.0

    def test_default_job_requirement_is_the_floor(self) -> None:
        """Defaulting to S1 made every job posted without touching the field
        silently demand a degree, zeroing this term for exactly the SMA/SMK
        school-leavers the product targets."""
        from backend.app.db.schemas import EducationLevel, JobPosting

        job = JobPosting(employer_id="e1", title="Kasir", description="x", region_code="3171")
        assert job.education_min == EducationLevel.SMA

    def test_hybrid_has_no_flat_bonus_left(self) -> None:
        # zero similarity, zero skills, unmet experience, no education = 0.
        assert _hybrid_score(0.0, 0.0, 0.0, 3, 0.0) == 0.0


class TestScorePair:
    def test_proof_moves_the_live_score(self) -> None:
        job = JobPosting(employer_id="e", title="Kasir", description="d", region_code="3171",
                         required_skills=["Kasir", "Excel"], education_min="SMA")
        before = SeekerProfile(user_id="u", full_name="A", region_code="3171",
                               skills=[Skill(name="Kasir"), Skill(name="Excel")])
        after = before.model_copy(deep=True)
        after.skills[0].proof_level, after.skills[0].proof_date = "quiz", TODAY
        assert score_pair(after, job)["score"] > score_pair(before, job)["score"]


class TestProofIntegrity:
    def test_carry_proof_keeps_earned_badges(self) -> None:
        old = [Skill(name="Excel", proof_level="quiz", proof_date=TODAY),
               Skill(name="Kasir", proof_level="hr_confirmed")]
        new = carry_proof([Skill(name="excel"), Skill(name="Sales")], old)
        by_name = {s.name.lower(): s.proof_level for s in new}
        assert by_name == {"excel": "quiz", "sales": "claimed", "kasir": "hr_confirmed"}

    def test_profile_api_cannot_forge_proof(
        self, client: TestClient, seeker_account: dict, stub_embedder
    ) -> None:
        h = seeker_account["headers"]
        client.post("/api/v1/seeker/profile", headers=h, json={
            "full_name": "Rina", "region_code": "3171",
            "skills": [{"name": "Excel", "proof_level": "hr_confirmed", "proof_date": TODAY}],
        })
        skills = client.get("/api/v1/seeker/profile", headers=h).json()["skills"]
        assert skills[0]["proof_level"] == "claimed"


class TestRedaction:
    def test_contact_data_is_removed(self) -> None:
        text = "Hubungi rina@mail.com / +62 812-3456-7890, NIK 3171123412341234."
        out = redact_text(text)
        assert "rina@mail.com" not in out and "3456" not in out and "3171123412341234" not in out
        assert "[email]" in out and "[nik]" in out and "[phone]" in out

    def test_llm_messages_are_redacted(self) -> None:
        from langchain_core.messages import HumanMessage

        out = redact_llm_input([HumanMessage(content="email saya a@b.co")])
        assert out[0].content == "email saya [email]"


class TestProofBeatsKeywordStuffing:
    """The product's headline claim, asserted against the real formula.

    Cosine rewards a CV that reads like the advert — which is precisely what
    keyword stuffing produces. So the two weights are in direct competition,
    and the claim "kata kunci di CV tidak lagi menang" is only true while the
    proof term can outrun the cosine a stuffer can manufacture.
    """

    def test_a_proven_candidate_beats_a_stuffer(self) -> None:
        # Stuffer echoes the advert (very high cosine) but proves nothing.
        stuffer = _hybrid_score(0.90, 0.30, 2, 1, 1.0)
        # Honest candidate reads nothing like the advert, but proved every skill.
        proven = _hybrid_score(0.50, 0.85, 2, 1, 1.0)
        assert proven > stuffer, (
            f"stuffing wins ({stuffer:.4f} vs {proven:.4f}) — the pitch claims "
            "the opposite. Raise _W_SKILL relative to _W_COSINE."
        )

    def test_cosine_cannot_outrun_full_proof_in_practice(self) -> None:
        """How much cosine advantage cancels proving every required skill.

        Cosine spans roughly 0.3-0.95 on real pairs, so a threshold above ~0.6
        means stuffing cannot buy its way past proof by any realistic margin.
        """
        from backend.app.services.matching.matcher import _W_COSINE, _W_SKILL

        needed = (0.85 - 0.30) * _W_SKILL / _W_COSINE
        assert needed > 0.60, f"only {needed:.3f} cosine advantage cancels full proof"

    def test_proof_outweighs_text_similarity(self) -> None:
        """The thesis, stated as an invariant: evidence counts for more than
        reading like the advert."""
        from backend.app.services.matching.matcher import _W_COSINE, _W_SKILL

        assert _W_SKILL > _W_COSINE

    def test_weights_still_sum_to_one(self) -> None:
        from backend.app.services.matching.matcher import (
            _W_COSINE,
            _W_EDUCATION,
            _W_EXPERIENCE,
            _W_SKILL,
        )

        assert _W_COSINE + _W_SKILL + _W_EXPERIENCE + _W_EDUCATION == pytest.approx(1.0)


class TestDisplayedWeightsMatchTheEngine:
    """Every surface that shows a weight must show the weight actually used.

    This drift has bitten repeatedly: the UI displayed cosine .45 / skill .25
    (summing to 0.70 and 0.95 in two components), README and PRODUCT_FEATURES
    carried a superseded formula, and `education_min` defaulted to SMA in the
    ORM while the SQL init path still said S1. A user shown one calculation and
    scored by another cannot check our working, which is the whole premise of a
    "transparent score".
    """

    # Files that quote the formula to a human. Add new ones here.
    _SURFACES = (
        "README.md",
        "docs/PRODUCT_FEATURES.md",
        "docs/internals/01-matching-algorithm.md",
        "frontend/src/components/SeekerDashboard.jsx",
        "frontend/src/components/SeekerMatchResults.jsx",
        "frontend/src/components/JobDetailModal.jsx",
        "frontend/src/components/EmployerHelpPanel.jsx",
    )

    def _repo_root(self):
        from pathlib import Path

        return Path(__file__).resolve().parents[3]

    def test_no_surface_quotes_a_weight_the_engine_does_not_use(self) -> None:
        import re

        from backend.app.services.matching.evidence import PROOF_WEIGHTS
        from backend.app.services.matching.matcher import (
            _W_COSINE,
            _W_EDUCATION,
            _W_EXPERIENCE,
            _W_SKILL,
        )

        # Factor weights AND proof weights: both are engine constants a surface
        # may legitimately quote (claimed 0.30 / quiz 0.85 / HR 1.00).
        live = {round(w * 100) for w in (_W_COSINE, _W_SKILL, _W_EXPERIENCE, _W_EDUCATION)}
        live |= {round(w * 100) for w in PROOF_WEIGHTS.values()}
        # "×0.35", "×.35", "* 0.35" — a multiplier shown next to a factor.
        pattern = re.compile(r"[×*]\s?0?\.(\d{2})")
        root = self._repo_root()
        offenders: list[str] = []
        for rel in self._SURFACES:
            path = root / rel
            if not path.exists():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for found in pattern.findall(line):
                    if int(found) not in live:
                        offenders.append(f"{rel}:{lineno} shows ×0.{found}")
        assert not offenders, (
            "displayed weights disagree with matcher.py "
            f"(live: {sorted(live)}): " + "; ".join(offenders)
        )

    def test_no_surface_still_describes_spark_as_first_come_first_served(self) -> None:
        """Spark reveals the top N BY SCORE. Copy saying "pelamar pertama"
        (first applicants) describes a queue — the behaviour this deliberately
        replaced — and an employer reading it would expect the wrong thing."""

        root = self._repo_root()
        offenders = []
        for sub in ("docs", "frontend/src", "backend/app", "README.md"):
            base = root / sub
            paths = [base] if base.is_file() else [
                p for p in base.rglob("*")
                if p.is_file() and p.suffix in {".md", ".jsx", ".js", ".py"}
                and "node_modules" not in p.parts and "__pycache__" not in p.parts
            ]
            for path in paths:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for phrase in ("pelamar pertama", "first 20 applicants"):
                    if phrase in text:
                        offenders.append(f"{path.relative_to(root)} says '{phrase}'")
        assert not offenders, "Spark copy still describes arrival order: " + "; ".join(offenders)

    def test_sql_init_path_matches_the_orm_education_default(self) -> None:
        """A database built from the SQL file must not demand a degree the ORM
        would not have demanded."""
        from backend.app.db.schemas import EducationLevel, JobPosting

        sql = (self._repo_root() / "backend/app/db/migrations/0001_init.sql").read_text(
            encoding="utf-8"
        )
        orm_default = JobPosting(
            employer_id="e1", title="x", description="x", region_code="3171"
        ).education_min
        assert orm_default == EducationLevel.SMA
        assert f"education_min education_level default '{orm_default.value}'" in sql


class TestResumeTextIsRedactedOnEveryPath:
    """Stored resume_text reaches the embedding API verbatim.

    matcher._build_seeker_text() puts resume_text into the text it sends to the
    Gemini embedding API — a path that never goes through llm_factory, so
    redact_llm_input never runs on it. Whatever is stored is what is sent, so
    the redaction has to happen at storage time on BOTH parse paths.
    """

    def test_gemini_path_stores_redacted_text(self) -> None:
        from backend.app.services.pdf_parser import _validate_cv_schema

        out = _validate_cv_schema({
            "resume_text": "Hubungi rina@mail.com atau 0812-3456-7890, NIK 3171123412341234",
            "full_name": "Rina", "skills": [], "experience": [], "education": [],
        })
        text = out["resume_text"]
        assert "rina@mail.com" not in text
        assert "3456" not in text
        assert "3171123412341234" not in text
        assert "[email]" in text and "[phone]" in text and "[nik]" in text

    def test_what_the_embedder_receives_carries_no_contact_data(self) -> None:
        from backend.app.db.schemas import SeekerProfile
        from backend.app.services.matching.matcher import _build_seeker_text
        from backend.app.services.pdf_parser import _validate_cv_schema

        parsed = _validate_cv_schema({
            "resume_text": "email rina@mail.com hp 0812-3456-7890",
            "full_name": "Rina", "skills": [], "experience": [], "education": [],
        })
        seeker = SeekerProfile(user_id="u1", full_name="Rina", region_code="3171",
                               resume_text=parsed["resume_text"])
        sent = _build_seeker_text(seeker)
        assert "rina@mail.com" not in sent and "3456" not in sent


class TestScannedPdfNeedsConsent:
    """A scan can only be sent as an image, so the seeker is asked first.

    Sending it means handing Gemini a picture of a CV carrying the very phone
    number and e-mail the regex exists to strip. Refusing outright would
    exclude the many Indonesian seekers whose CV is a phone photo, so the
    trade is informed consent: never silent, never blocked.
    """

    def test_text_pdf_is_redacted_and_sent_as_text(self) -> None:
        from backend.app.services.pdf_parser import _llm_contents

        class _FakeTypes:  # the real one is only imported inside the Gemini path
            class Part:
                @staticmethod
                def from_bytes(**kw):
                    raise AssertionError("a text PDF must never be sent as raw bytes")

        long_text = "Rina Kartika. Email rina@mail.com. Telepon 0812-3456-7890. " * 6
        parts = _llm_contents(_FakeTypes, b"%PDF-fake", _text_override=long_text)
        assert "rina@mail.com" not in parts[0]
        assert "[email]" in parts[0] and "[phone]" in parts[0]

    def test_scanned_pdf_is_not_sent_without_consent(self) -> None:
        import pytest as _pytest

        from backend.app.services.pdf_parser import ScannedPdfError, _llm_contents

        class _FakeTypes:
            class Part:
                @staticmethod
                def from_bytes(**kw):
                    raise AssertionError("must not send a scan before the seeker agrees")

        with _pytest.raises(ScannedPdfError) as err:
            _llm_contents(_FakeTypes, b"%PDF-scan", _text_override="")
        # The prompt must say what actually leaves the server, not just "failed".
        msg = str(err.value).lower()
        assert "gambar dokumen" in msg and "dikirim ke ai" in msg

    def test_scanned_pdf_is_sent_once_consent_is_given(self) -> None:
        from backend.app.services.pdf_parser import _llm_contents

        sent = {}

        class _FakeTypes:
            class Part:
                @staticmethod
                def from_bytes(**kw):
                    sent.update(kw)
                    return "PDF_PART"

        parts = _llm_contents(_FakeTypes, b"%PDF-scan", allow_scanned=True, _text_override="")
        assert parts[0] == "PDF_PART"
        assert sent["mime_type"] == "application/pdf"

    def test_consent_does_not_loosen_the_text_path(self) -> None:
        """Consent only unlocks the image branch. A PDF that HAS text is still
        redacted, never sent as bytes, whatever the flag says."""
        from backend.app.services.pdf_parser import _llm_contents

        class _FakeTypes:
            class Part:
                @staticmethod
                def from_bytes(**kw):
                    raise AssertionError("a text PDF must never be sent as raw bytes")

        long_text = "Rina. Email rina@mail.com. Telepon 0812-3456-7890. " * 6
        parts = _llm_contents(_FakeTypes, b"%PDF", allow_scanned=True, _text_override=long_text)
        assert "rina@mail.com" not in parts[0] and "[email]" in parts[0]
