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
        body = client.get("/api/v1/quiz/skills", headers=seeker_h).json()
        keys = {b["skill"] for b in body["bank"]}
        assert {"excel", "customer service", "kasir"} <= keys

    def test_start_never_sends_answers(self, client: TestClient, seeker_h: dict) -> None:
        attempt = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h).json()
        assert len(attempt["questions"]) == 5
        assert "correct_index" not in str(attempt)
        assert attempt["draft_bank"] is True  # starter bank still awaits HR review

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
        assert result["passed"] is False and result["retake_after_days"] == 7
        again = client.post("/api/v1/quiz/start", json={"skill": "Excel"}, headers=seeker_h)
        assert again.status_code == 429

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

    def test_unknown_skill_is_404(self, client: TestClient, seeker_h: dict) -> None:
        assert client.post("/api/v1/quiz/start", json={"skill": "Juggling"},
                           headers=seeker_h).status_code == 404

    def test_employers_cannot_take_quizzes(self, client: TestClient, employer_account: dict) -> None:
        assert client.post("/api/v1/quiz/start", json={"skill": "Excel"},
                           headers=employer_account["headers"]).status_code == 403
