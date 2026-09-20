"""v2 proof-weighted scoring, education fit, redaction and proof integrity."""

from __future__ import annotations

from datetime import date, timedelta

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

TODAY = date.today().isoformat()


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
        old = (date.today() - timedelta(days=181)).isoformat()
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
        assert education_fit([], "SMA") == 0.0

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
