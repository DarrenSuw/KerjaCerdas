"""AutoMod, first-job review, reports, appeals, strikes, admin review, badges."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.config.settings import settings
from backend.app.services.trust.automod import check_rules
from backend.app.services.trust.policy import employer_badges

JOB = {"title": "Admin Toko", "description": "Mengelola stok dan melayani pelanggan.",
       "required_skills": ["Excel", "Customer Service"], "education_min": "SMA",
       "region_code": "3171", "salary_min": 4_000_000, "salary_max": 5_000_000}


def _post(client: TestClient, headers: dict, **over) -> dict:
    resp = client.post("/api/v1/employer/jobs", json={**JOB, **over}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def admin(client: TestClient, register, monkeypatch: pytest.MonkeyPatch) -> dict:
    acct = register(client, "seeker")
    monkeypatch.setattr(settings, "admin_routes_enabled", True)
    monkeypatch.setattr(settings, "admin_emails", [acct["email"]])
    return acct


class TestRules:
    def test_fee_request_is_rejected(self) -> None:
        v = check_rules("Kasir", "Pelamar wajib bayar biaya seragam Rp300.000.", [])
        assert v.decision == "rejected" and v.reasons[0]["rule"] == "fee_to_candidate"
        assert "seragam" in v.reasons[0]["excerpt"]

    def test_discriminatory_terms_are_held(self) -> None:
        assert check_rules("SPG", "Usia maksimal 25 tahun, berpenampilan menarik.", []).decision == "held"

    def test_clean_ad_is_published(self) -> None:
        assert check_rules(JOB["title"], JOB["description"], []).decision == "published"


class TestPostingFlow:
    def test_rejected_post_gets_notice_and_strike(self, client: TestClient, employer_account: dict,
                                                  stub_embedder) -> None:
        body = _post(client, employer_account["headers"],
                     description="Wajib transfer biaya pelatihan Rp500.000 sebelum mulai.")
        assert body["moderation_status"] == "rejected"
        assert body["strike"]["strikes"] == 1
        assert "biaya" in body["notice"].lower()
        public = client.get(f"/api/v1/public/jobs/{body['public_code']}").json()
        assert public["accepting_applications"] is False

    def test_edit_and_resubmit_publishes(self, client: TestClient, employer_account: dict,
                                         stub_embedder) -> None:
        h = employer_account["headers"]
        job = _post(client, h, description="Syarat: berpenampilan menarik.")
        assert job["moderation_status"] == "held"
        fixed = client.patch(f"/api/v1/employer/jobs/{job['job_id']}", headers=h,
                             json={"description": "Teliti dan rapi dalam administrasi."}).json()
        assert fixed["moderation_status"] == "published"

    def test_first_job_is_held_when_review_is_on(self, client: TestClient, employer_account: dict,
                                                 stub_embedder, monkeypatch) -> None:
        monkeypatch.setattr(settings, "moderation_first_job_review", True)
        first = _post(client, employer_account["headers"])
        assert first["moderation_status"] == "held"
        assert first["moderation_reasons"][-1]["rule"] == "first_job_review"
        second = _post(client, employer_account["headers"], title="Staf Gudang")
        assert second["moderation_status"] == "published"

    def test_three_strikes_suspend_posting(self, client: TestClient, employer_account: dict,
                                           stub_embedder) -> None:
        bad = "Bayar biaya administrasi Rp200.000."
        for _ in range(3):
            _post(client, employer_account["headers"], description=bad)
        resp = client.post("/api/v1/employer/jobs", json=JOB, headers=employer_account["headers"])
        assert resp.status_code == 403

    def test_reports_hide_a_job(self, client: TestClient, employer_account: dict, register,
                                stub_embedder, monkeypatch) -> None:
        monkeypatch.setattr(settings, "moderation_report_threshold", 2)
        code = _post(client, employer_account["headers"])["public_code"]
        for _ in range(2):
            reporter = register(client, "seeker")
            r = client.post(f"/api/v1/public/jobs/{code}/report", headers=reporter["headers"],
                            json={"reason": "palsu"})
        assert r.json()["job_hidden_for_review"] is True
        assert client.get(f"/api/v1/public/jobs/{code}").json()["moderation_status"] == "held"

    def test_report_requires_login(self, client: TestClient, employer_account: dict,
                                   stub_embedder) -> None:
        code = _post(client, employer_account["headers"])["public_code"]
        assert client.post(f"/api/v1/public/jobs/{code}/report", json={"reason": "palsu"}).status_code == 401


class TestAdmin:
    def test_non_admin_is_refused(self, client: TestClient, seeker_account: dict) -> None:
        assert client.get("/api/v1/admin/moderation/queue",
                          headers=seeker_account["headers"]).status_code == 403

    def test_appeal_then_admin_publishes(self, client: TestClient, employer_account: dict,
                                         admin: dict, stub_embedder) -> None:
        h = employer_account["headers"]
        job = _post(client, h, description="Khusus pria karena pekerjaan angkat barang berat.")
        assert job["moderation_status"] == "held"
        client.post(f"/api/v1/employer/jobs/{job['job_id']}/appeal", headers=h,
                    json={"message": "Pekerjaan angkat beban 50kg, alasan K3."})
        queue = client.get("/api/v1/admin/moderation/queue", headers=admin["headers"]).json()
        assert any(i["job_id"] == job["job_id"] for i in queue["items"])
        out = client.post(f"/api/v1/admin/moderation/jobs/{job['job_id']}", headers=admin["headers"],
                          json={"decision": "publish", "note": "Alasan K3 masuk akal"}).json()
        assert out["moderation_status"] == "published"

    def test_admin_review_badge(self, client: TestClient, employer_account: dict, admin: dict) -> None:
        h = employer_account["headers"]
        client.post("/api/v1/employer/trust/review-request", headers=h,
                    json={"links": ["https://maps.google.com/?q=toko"]})
        pending = client.get("/api/v1/admin/employer-reviews", headers=admin["headers"]).json()["items"]
        client.post(f"/api/v1/admin/employer-reviews/{pending[0]['employer_id']}",
                    headers=admin["headers"], json={"approve": True})
        badges = client.get("/api/v1/employer/trust", headers=h).json()["badges"]
        assert badges["admin_reviewed"] is True


class TestBadges:
    def test_company_email_needs_matching_domain_and_verification(self) -> None:
        from types import SimpleNamespace

        emp = SimpleNamespace(website="https://www.tokomaju.co.id", verified="unverified")
        ok = SimpleNamespace(email="hr@tokomaju.co.id", email_verified=True)
        free = SimpleNamespace(email="tokomaju@gmail.com", email_verified=True)
        unverified = SimpleNamespace(email="hr@tokomaju.co.id", email_verified=False)
        assert employer_badges(emp, ok)["company_email"] is True
        assert employer_badges(emp, free)["company_email"] is False
        assert employer_badges(emp, unverified)["company_email"] is False


class TestMetrics:
    def test_cost_per_action_and_outcomes(self, client: TestClient, admin: dict) -> None:
        import asyncio

        from backend.app.db.postgres_store import record_ai_usage

        asyncio.run(record_ai_usage("cv_parser", "gemini-3.5-flash-lite", 5000, 1500, 900))
        m = client.get("/api/v1/admin/metrics", headers=admin["headers"]).json()
        cv = m["ai_cost_by_task"]["cv_parser"]
        # 5k in x $0.30/1M + 1.5k out x $2.50/1M = $0.00525 x Rp17,600 ~= Rp92
        assert 90 <= cv["avg_cost_idr_per_call"] <= 95
        assert {"applications", "outcomes_by_band", "quizzes", "plans", "moderation"} <= set(m)


class TestAdminFlagOnLogin:
    """The login response advertises admin rights so the UI can show the entry
    point. It is only a hint: every /admin route re-checks server-side.
    """

    def test_ordinary_account_is_not_admin(self, client: TestClient, seeker_account: dict) -> None:
        assert seeker_account["user"]["is_admin"] is False

    def test_listed_email_is_admin_on_login(self, client: TestClient, admin: dict) -> None:
        resp = client.post("/api/v1/auth/login",
                           json={"email": admin["email"], "password": admin["password"]})
        assert resp.status_code == 200, resp.text
        assert resp.json()["user"]["is_admin"] is True

    def test_flag_follows_the_switch_not_the_token(
        self, client: TestClient, admin: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Turning ADMIN_ROUTES_ENABLED off revokes access for an existing token."""
        monkeypatch.setattr(settings, "admin_routes_enabled", False)
        assert client.get("/api/v1/admin/metrics", headers=admin["headers"]).status_code == 403
        resp = client.post("/api/v1/auth/login",
                           json={"email": admin["email"], "password": admin["password"]})
        assert resp.json()["user"]["is_admin"] is False

    def test_metrics_shape_is_stable_when_empty(self, client: TestClient, admin: dict) -> None:
        body = client.get("/api/v1/admin/metrics", headers=admin["headers"]).json()
        for key in ("ai_cost_by_task", "applications", "outcomes_by_band",
                    "quizzes", "plans", "moderation", "usd_to_idr"):
            assert key in body, key
