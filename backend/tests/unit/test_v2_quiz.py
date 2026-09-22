"""Skill quizzes: no answer leakage, server-side grading, proof, cooldown."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.app.db import postgres_store as store
from backend.app.services.quiz.service import option_order


def _profile(client: TestClient, headers: dict) -> None:
    resp = client.post("/api/v1/seeker/profile", headers=headers,
                       json={"full_name": "Rina", "region_code": "3171", "skills": ["Excel"]})
    assert resp.status_code in (200, 201), resp.text


def _answers(attempt: dict, right: bool) -> list[int]:
    bank = {q.id: q for q in asyncio.run(store.find_active_questions(attempt["skill"]))}
    out = []
    for q in attempt["questions"]:
        orig = bank[q["id"]]
        order = option_order(attempt["attempt_id"], q["id"], len(orig.options))
        shown_correct = order.index(orig.correct_index)
        out.append(shown_correct if right else (shown_correct + 1) % len(orig.options))
    return out


@pytest.fixture
def seeker_h(client: TestClient, seeker_account: dict, stub_embedder) -> dict:
    _profile(client, seeker_account["headers"])
    return seeker_account["headers"]


class TestQuiz:
    def test_bank_is_seeded_and_listed(self, client: TestClient, seeker_h: dict) -> None:
        from backend.app.services.matching.evidence import skill_key

        body = client.get("/api/v1/quiz/skills", headers=seeker_h).json()
        keys = {skill_key(b["skill"]) for b in body["bank"]}
        assert keys == {skill_key("Excel")}

    def test_new_profile_skill_becomes_eligible_for_quiz(self, client: TestClient, seeker_h: dict) -> None:
        from backend.app.services.matching.evidence import skill_key

        resp = client.post("/api/v1/seeker/profile", headers=seeker_h,
                           json={"full_name": "Rina", "region_code": "3171", "skills": ["Excel", "Kasir"]})
        assert resp.status_code in (200, 201), resp.text
        body = client.get("/api/v1/quiz/skills", headers=seeker_h).json()
        names = {skill_key(item["skill"]) for item in body["items"]}
        bank_names = {skill_key(item["skill"]) for item in body["bank"]}
        assert {skill_key("Excel"), skill_key("Kasir")} <= names
        assert {skill_key("Excel"), skill_key("Kasir")} <= bank_names

    def test_start_never_sends_answers(self, client: TestClient, seeker_h: dict) -> None:
        attempt = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).json()
        assert len(attempt["questions"]) == 5
        assert "correct_index" not in str(attempt)
        assert attempt["draft_bank"] is False  # starter bank is now seeded as reviewed=True

    def test_validate_question_rejects_misaligned_correct_index(self) -> None:
        from backend.app.services.quiz import generator

        reason = generator.validate_question(
            "Manakah langkah paling aman saat menerima uang tunai di kasir?",
            ["Lanjutkan tanpa cek", "Mencatat transaksi dan mengecek kembalian", "Minta uang tambahan", "Tutup kasir"],
            4,
        )
        assert reason == "correct_index tidak sesuai dengan opsi yang tersedia"

    def test_pass_gives_quiz_proof(self, client: TestClient, seeker_h: dict) -> None:
        attempt = client.post("/api/v1/quiz/start", json={"skill": "MS Excel"}, headers=seeker_h).json()
        result = client.post("/api/v1/quiz/submit", headers=seeker_h, json={
            "attempt_id": attempt["attempt_id"], "answers": _answers(attempt, right=True)}).json()
        assert result["passed"] is True and result["score"] == 5
        skills = client.get("/api/v1/seeker/profile", headers=seeker_h).json()["skills"]
        excel = next(s for s in skills if s["name"].lower() == "excel")
        assert excel["proof_level"] == "quiz" and excel["proof_date"]

    def test_passing_a_new_skill_adds_it(self, client: TestClient, seeker_h: dict) -> None:
        attempt = client.post("/api/v1/quiz/start", json={"skill": "Kasir"}, headers=seeker_h).json()
        client.post("/api/v1/quiz/submit", headers=seeker_h, json={
            "attempt_id": attempt["attempt_id"], "answers": _answers(attempt, right=True)})
        names = [s["name"] for s in client.get("/api/v1/seeker/profile", headers=seeker_h).json()["skills"]]
        assert "Kasir" in names

    def test_fail_triggers_cooldown(self, client: TestClient, seeker_h: dict) -> None:
        attempt = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).json()
        result = client.post("/api/v1/quiz/submit", headers=seeker_h, json={
            "attempt_id": attempt["attempt_id"], "answers": _answers(attempt, right=False)}).json()
        assert result["passed"] is False and result["retake_after_days"] == 1
        again = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h)
        assert again.status_code == 429

    @pytest.mark.asyncio
    async def test_abandoned_attempt_counts_as_used_only_after_thirty_seconds(self, client: TestClient, seeker_h: dict, seeker_account: dict) -> None:
        from datetime import UTC, datetime, timedelta

        from backend.app.db import postgres_store as store
        from backend.app.services.quiz import service

        start = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).json()
        repos = store.get_repositories()
        attempt = await repos.quiz_attempts.get(start["attempt_id"])
        assert attempt is not None
        attempt.created_at = datetime.now(UTC) - timedelta(seconds=31)
        await repos.quiz_attempts.upsert(attempt)

        seeker = await store.find_seeker_by_user_id(seeker_account["user"]["id"])
        assert seeker is not None
        result = await service.abandon_quiz(seeker, start["attempt_id"], elapsed_seconds=31)
        assert result["status"] == "abandoned"
        assert result["used_attempt"] is True
        assert client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).status_code == 429

    @pytest.mark.asyncio
    async def test_short_exit_does_not_count_as_attempt(self, client: TestClient, seeker_h: dict, seeker_account: dict) -> None:
        from backend.app.db import postgres_store as store
        from backend.app.services.quiz import service

        start = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).json()
        seeker = await store.find_seeker_by_user_id(seeker_account["user"]["id"])
        assert seeker is not None
        result = await service.abandon_quiz(seeker, start["attempt_id"], elapsed_seconds=29)
        assert result["status"] == "in_progress"
        assert result["used_attempt"] is False
        again = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h)
        assert again.status_code == 200

    def test_open_attempt_is_resumed_not_redrawn(self, client: TestClient, seeker_h: dict) -> None:
        a = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).json()
        b = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).json()
        assert a["attempt_id"] == b["attempt_id"] and b["resumed"] is True

    def test_double_submit_is_rejected(self, client: TestClient, seeker_h: dict) -> None:
        attempt = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).json()
        body = {"attempt_id": attempt["attempt_id"], "answers": _answers(attempt, right=True)}
        assert client.post("/api/v1/quiz/submit", headers=seeker_h, json=body).status_code == 200
        assert client.post("/api/v1/quiz/submit", headers=seeker_h, json=body).status_code == 409

    def test_attempt_is_owner_only(self, client: TestClient, seeker_h: dict,
                                   other_seeker_account: dict) -> None:
        attempt = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).json()
        other = other_seeker_account["headers"]
        _profile(client, other)
        resp = client.post("/api/v1/quiz/submit", headers=other,
                           json={"attempt_id": attempt["attempt_id"], "answers": [0] * 5})
        assert resp.status_code == 404

    def test_unbanked_skill_not_on_the_profile_cannot_trigger_generation(
        self, client: TestClient, seeker_h: dict
    ) -> None:
        """An invented skill name must not reach the paid generator.

        A skill with no bank costs ~Rp85-130 of Gemini to create, so letting any
        logged-in user summon one by typing a name was a griefing vector: the
        attacker gains nothing and we pay per name. Claiming the skill first is
        the cheap, honest gate.
        """
        resp = client.post("/api/v1/quiz/start", json={"skill": "Juggling"}, headers=seeker_h)
        assert resp.status_code == 400
        assert "profilmu" in resp.json()["detail"]

    def test_employers_cannot_take_quizzes(self, client: TestClient, employer_account: dict) -> None:
        assert client.post("/api/v1/quiz/start", json={"skill": "Excel"},
                           headers=employer_account["headers"]).status_code == 403


class TestColdStartSkill:
    """A skill nobody has banked yet must not be served an unreviewed quiz."""

    @pytest.mark.asyncio
    async def test_generation_happens_once_not_per_attempt(self, monkeypatch) -> None:
        """The old dedupe used a reviewed-only query, which a freshly generated
        (reviewed=False) batch could never satisfy — so every call regenerated
        and re-billed Gemini while never becoming serveable."""
        from backend.app.db import postgres_store as store
        from backend.app.db.schemas_proof import SkillQuestion
        from backend.app.services.quiz import generator

        calls = {"n": 0}

        async def fake_generate(skill_name: str, count: int = 10, existing=None):
            calls["n"] += 1
            return [
                SkillQuestion(skill="forklift", skill_label="Forklift",
                              question=f"Q{i}", options=["a", "b", "c", "d"],
                              correct_index=0, reviewed=False)
                for i in range(6)
            ]

        monkeypatch.setattr(generator, "generate_questions", fake_generate)
        assert await generator.ensure_questions_exist("forklift", target=6) > 0
        assert calls["n"] == 1
        # Second call must be a no-op: the rows exist, they are just unreviewed.
        assert await generator.ensure_questions_exist("forklift", target=6) == 0
        assert calls["n"] == 1
        assert await store.count_active_questions_for_skill("forklift") == 6

    @pytest.mark.asyncio
    async def test_unreviewed_skill_is_not_offered_or_served(self, monkeypatch) -> None:
        from backend.app.db import postgres_store as store
        from backend.app.db.schemas import SeekerProfile, Skill
        from backend.app.db.schemas_proof import SkillQuestion
        from backend.app.services.quiz import generator, service

        repos = store.get_repositories()
        for i in range(6):
            await repos.skill_questions.upsert(
                SkillQuestion(skill="forklift", skill_label="Forklift", question=f"Q{i}",
                              options=["a", "b", "c", "d"], correct_index=0, reviewed=False)
            )
        # Never advertised, because it cannot be served.
        assert "forklift" not in {s["skill"] for s in await store.list_quiz_skills()}

        async def no_generate(skill_name: str, count: int = 10, existing=None):  # already has rows; must not be called
            raise AssertionError("must not regenerate for a skill that already has questions")

        async def failing_generate(skill_name: str, count: int = 10, existing=None):
            raise generator.GenerationError("belum bisa dibuat")

        monkeypatch.setattr(generator, "generate_questions", failing_generate)
        # The seeker claims the skill, so generation is allowed to be attempted —
        # this test is about what happens to the UNREVIEWED rows already there.
        seeker = SeekerProfile(
            user_id="u-cold", full_name="Dewi", region_code="3171",
            skills=[Skill(name="Forklift")],
        )
        with pytest.raises(service.QuizError) as err:
            await service.start_quiz(seeker, "forklift")
        # Unreviewed rows exist but are invisible to the server, so the bank is
        # still unusable and nothing is drawn from them.
        assert err.value.status == 503
        assert "belum siap" in err.value.message or "sedang disiapkan" in err.value.message
        _ = no_generate

    @pytest.mark.asyncio
    async def test_reviewing_the_batch_makes_it_live(self) -> None:
        from backend.app.db import postgres_store as store
        from backend.app.db.schemas_proof import SkillQuestion

        repos = store.get_repositories()
        made = []
        for i in range(6):
            q = SkillQuestion(skill="forklift", skill_label="Forklift", question=f"Q{i}",
                              options=["a", "b", "c", "d"], correct_index=0, reviewed=False)
            await repos.skill_questions.upsert(q)
            made.append(q)
        for q in made:
            q.reviewed = True
            await repos.skill_questions.upsert(q)
        assert "forklift" in {s["skill"] for s in await store.list_quiz_skills()}
        assert len(await store.find_active_questions("forklift")) == 6


class TestBankReplenishment:
    """Deactivating bad questions must not wedge a skill permanently."""

    @pytest.mark.asyncio
    async def test_deactivated_questions_free_the_bank_to_refill(self, monkeypatch) -> None:
        """Counting ALL rows would leave dead rows satisfying the threshold, so
        a skill whose questions were deactivated could never be replenished."""
        from backend.app.db import postgres_store as store
        from backend.app.db.schemas_proof import SkillQuestion
        from backend.app.services.quiz import generator

        repos = store.get_repositories()
        made = []
        for i in range(6):
            q = SkillQuestion(skill="forklift", skill_label="Forklift", question=f"Q{i}",
                              options=["a", "b", "c", "d"], correct_index=0, reviewed=False)
            await repos.skill_questions.upsert(q)
            made.append(q)

        calls = {"n": 0}

        async def fake_generate(skill_name: str, count: int = 10, existing=None):
            calls["n"] += 1
            return [
                SkillQuestion(skill="forklift", skill_label="Forklift", question=f"N{i}",
                              options=["a", "b", "c", "d"], correct_index=0, reviewed=False)
                for i in range(6)
            ]

        monkeypatch.setattr(generator, "generate_questions", fake_generate)

        # Pending drafts block regeneration — they are on their way to serveable.
        assert await generator.ensure_questions_exist("forklift", target=6) == 0
        assert calls["n"] == 0

        # An admin finds the batch unusable and deactivates it.
        for q in made:
            q.active = False
            await repos.skill_questions.upsert(q)
        assert await store.count_active_questions_for_skill("forklift") == 0

        # The bank must now be allowed to refill.
        assert await generator.ensure_questions_exist("forklift", target=6) > 0
        assert calls["n"] == 1
        assert await store.count_active_questions_for_skill("forklift") == 6

    @pytest.mark.asyncio
    async def test_partial_deactivation_tops_the_bank_back_up(self, monkeypatch) -> None:
        from backend.app.db import postgres_store as store
        from backend.app.db.schemas_proof import SkillQuestion
        from backend.app.services.quiz import generator

        repos = store.get_repositories()
        made = []
        for i in range(6):
            q = SkillQuestion(skill="forklift", skill_label="Forklift", question=f"Q{i}",
                              options=["a", "b", "c", "d"], correct_index=0, reviewed=True)
            await repos.skill_questions.upsert(q)
            made.append(q)

        async def fake_generate(skill_name: str, count: int = 10, existing=None):
            return [
                SkillQuestion(skill="forklift", skill_label="Forklift", question=f"N{i}",
                              options=["a", "b", "c", "d"], correct_index=0, reviewed=False)
                for i in range(6)
            ]

        monkeypatch.setattr(generator, "generate_questions", fake_generate)
        # Two questions retired -> 4 active, below the 5 a quiz needs.
        for q in made[:2]:
            q.active = False
            await repos.skill_questions.upsert(q)
        assert await store.count_active_questions_for_skill("forklift") == 4
        assert await generator.ensure_questions_exist("forklift", target=6) > 0
        assert await store.count_active_questions_for_skill("forklift") == 10
