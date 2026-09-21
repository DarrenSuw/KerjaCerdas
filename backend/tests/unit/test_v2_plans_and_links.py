"""Plans (Spark/Beacon/Lighthouse/Prism), share links + QR, apply data."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.config.settings import settings

JOB = {"title": "Kasir Kafe", "description": "Melayani transaksi pelanggan.",
       "required_skills": ["Kasir", "Customer Service"], "education_min": "SMA",
       "region_code": "3171", "salary_min": 3_500_000, "salary_max": 4_500_000}


@pytest.fixture
def admin(client: TestClient, register, monkeypatch: pytest.MonkeyPatch) -> dict:
    acct = register(client, "seeker")
    import asyncio

    from sqlalchemy import text

    from backend.app.api import database as db_mod
    async def _verify():
        async with db_mod.engine.begin() as conn:
            await conn.execute(text("UPDATE users SET email_verified=1 WHERE email=:email").bindparams(email=acct["email"]))
    asyncio.run(_verify())

    monkeypatch.setattr(settings, "admin_routes_enabled", True)
    monkeypatch.setattr(settings, "admin_emails", [acct["email"]])
    return acct


@pytest.fixture
def limits_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "plan_limits_enforced", True)


def _job(client, h, **over) -> dict:
    resp = client.post("/api/v1/employer/jobs", json={**JOB, **over}, headers=h)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _apply(client, register, job_id: str, **extra) -> dict:
    seeker = register(client, "seeker")
    client.post("/api/v1/seeker/profile", headers=seeker["headers"],
                json={"full_name": "Dewi", "region_code": "3171", "skills": ["Kasir"]})
    resp = client.post("/api/v1/seeker/apply", headers=seeker["headers"],
                       json={"job_id": job_id, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestPlans:
    def test_catalogue_is_public(self, client: TestClient) -> None:
        body = client.get("/api/v1/billing/plans").json()
        prices = {p["plan"]: p["price_idr"] for p in body["employer"] + body["seeker"]}
        assert prices == {"spark": 0, "beacon": 49_000, "lighthouse": 149_000, "free": 0, "prism": 15_000}

    def test_spark_allows_one_active_job(self, client, employer_account, stub_embedder, limits_on):
        h = employer_account["headers"]
        _job(client, h)
        resp = client.post("/api/v1/employer/jobs", json={**JOB, "title": "Barista"}, headers=h)
        assert resp.status_code == 402

    def test_lighthouse_order_activation_lifts_limit(self, client, employer_account, admin,
                                                     stub_embedder, limits_on):
        h = employer_account["headers"]
        _job(client, h)
        order = client.post("/api/v1/billing/orders", headers=h, json={"plan": "lighthouse"}).json()
        assert order["status"] == "pending" and order["amount_idr"] == 149_000
        client.post(f"/api/v1/admin/orders/{order['order_id']}/activate", headers=admin["headers"])
        assert client.post("/api/v1/employer/jobs", json={**JOB, "title": "Barista"},
                           headers=h).status_code == 201

    def test_seeker_cannot_buy_employer_plans(self, client, seeker_account) -> None:
        resp = client.post("/api/v1/billing/orders", headers=seeker_account["headers"],
                           json={"plan": "lighthouse"})
        assert resp.status_code == 400

    def test_spark_reveals_the_BEST_n_not_the_first_n(
        self, client, employer_account, register, admin, stub_embedder, limits_on, monkeypatch
    ):
        """Spark is the tier every employer meets first, so it is the one that
        has to demonstrate that ranking works. Capping by arrival hid the best
        candidate whenever they applied late — a queue, not a ranking."""
        monkeypatch.setattr(settings, "spark_ranked_applicant_limit", 1)
        h = employer_account["headers"]
        job = _job(client, h)

        # Applies FIRST, matches neither required skill.
        weak = register(client, "seeker")
        client.post("/api/v1/seeker/profile", headers=weak["headers"],
                    json={"full_name": "Weak", "region_code": "3171", "skills": ["Menyapu"]})
        client.post("/api/v1/seeker/apply", headers=weak["headers"], json={"job_id": job["job_id"]})

        # Applies SECOND, holds both required skills.
        strong = register(client, "seeker")
        client.post("/api/v1/seeker/profile", headers=strong["headers"],
                    json={"full_name": "Strong", "region_code": "3171",
                          "skills": ["Kasir", "Customer Service"]})
        client.post("/api/v1/seeker/apply", headers=strong["headers"], json={"job_id": job["job_id"]})

        items = client.get("/api/v1/employer/applications", headers=h).json()["items"]
        visible = [i for i in items if not i["locked"]]
        assert len(visible) == 1, "the cap must reveal exactly spark_ranked_applicant_limit"
        # The late-arriving better candidate is the one shown.
        assert visible[0]["seeker_name"] == "Strong"

    def test_spark_ranks_only_first_n_and_premium_tools_are_gated(
        self, client, employer_account, register, admin, stub_embedder, limits_on, monkeypatch
    ):
        monkeypatch.setattr(settings, "spark_ranked_applicant_limit", 1)
        h = employer_account["headers"]
        job = _job(client, h)
        _apply(client, register, job["job_id"])
        _apply(client, register, job["job_id"])
        items = client.get("/api/v1/employer/applications", headers=h).json()["items"]
        assert [i["locked"] for i in items] == [False, True]
        app_id = items[0]["application_id"]
        assert client.get(f"/api/v1/employer/applications/{app_id}/interview-kit",
                          headers=h).status_code == 402

        order = client.post("/api/v1/billing/orders", headers=h,
                            json={"plan": "beacon", "job_id": job["job_id"]}).json()
        client.post(f"/api/v1/admin/orders/{order['order_id']}/activate", headers=admin["headers"])
        items = client.get("/api/v1/employer/applications", headers=h).json()["items"]
        assert not any(i["locked"] for i in items)
        kit = client.get(f"/api/v1/employer/applications/{app_id}/interview-kit", headers=h).json()
        assert kit["source"] == "template" and kit["questions"]
        csv = client.get(f"/api/v1/employer/jobs/{job['job_id']}/applicants.csv", headers=h)
        assert csv.status_code == 200 and csv.text.startswith("nama,email,skor")

    def test_advisor_free_quota(self, client, seeker_account, employer_account, stub_embedder,
                                stub_llm, limits_on, monkeypatch):
        from backend.app.services.billing import plans

        monkeypatch.setattr(plans, "ADVISOR_FREE_PER_DAY", 1)
        _job(client, employer_account["headers"])  # a relevant job so the LLM path runs
        h = seeker_account["headers"]
        client.post("/api/v1/seeker/profile", headers=h,
                    json={"full_name": "A", "region_code": "3171", "skills": ["Kasir"]})
        first = client.post("/api/v1/agent/invoke", headers=h, json={"user_message": "halo"})
        assert first.status_code == 200 and not first.json().get("early_exit")
        second = client.post("/api/v1/agent/invoke", headers=h, json={"user_message": "halo lagi"})
        assert second.status_code == 429 and "Prism" in second.json()["detail"]


class TestLinksAndApply:
    def test_public_page_and_qr(self, client, employer_account, stub_embedder) -> None:
        job = _job(client, employer_account["headers"])
        assert job["share_path"] == f"/j/{job['public_code']}"
        page = client.get(f"/api/v1/public/jobs/{job['public_code'].lower()}").json()
        assert page["title"] == JOB["title"] and "badges" in page and "embedding" not in page
        qr = client.get(f"/api/v1/public/jobs/{job['public_code']}/qr.svg?origin=http://evil.example")
        assert qr.status_code == 200 and qr.headers["content-type"].startswith("image/svg+xml")

    def test_apply_stores_score_snapshot_and_source(self, client, employer_account, register,
                                                   stub_embedder) -> None:
        job = _job(client, employer_account["headers"])
        body = _apply(client, register, job["job_id"], source="link")
        assert body["match_score"] > 0 and body["skill_proof"]
        items = client.get("/api/v1/employer/applications",
                           headers=employer_account["headers"]).json()["items"]
        assert items[0]["source"] == "link" and items[0]["match_score_at_apply"] == body["match_score"]

    def test_reverse_matching_is_refused_on_the_free_tier(
        self, client, employer_account, register, stub_embedder, limits_on
    ) -> None:
        """Sourcing is the employer feature that is actually sold.

        `talent_search_limit()` existed and was unit tested, but no router ever
        called it — so Spark's documented quota of zero meant unlimited in
        practice and the paid tiers bought nothing. Ranked APPLICANTS stay free
        and uncapped; this guards the boundary between the two.
        """
        job = _job(client, employer_account["headers"])
        seeker = register(client, "seeker")
        client.post("/api/v1/seeker/profile", headers=seeker["headers"], json={
            "full_name": "Nama Asli", "region_code": "3171", "skills": ["Kasir"]})
        resp = client.post(f"/api/v1/employer/jobs/{job['job_id']}/candidates",
                           headers=employer_account["headers"], json={})
        assert resp.status_code == 402, resp.text
        assert "Beacon" in resp.json()["detail"]

    def test_ranked_applicants_stay_free_while_sourcing_is_paid(
        self, client, employer_account, register, stub_embedder, limits_on
    ) -> None:
        """The paywall must sit on sourcing, never on screening."""
        job = _job(client, employer_account["headers"])
        seeker = register(client, "seeker")
        client.post("/api/v1/seeker/profile", headers=seeker["headers"], json={
            "full_name": "Pelamar", "region_code": "3171", "skills": ["Kasir"]})
        client.post(f"/api/v1/public/jobs/{job['public_code']}/apply", headers=seeker["headers"])
        # Screening: free, on the free tier, with no quota.
        apps = client.get("/api/v1/employer/applications", headers=employer_account["headers"])
        assert apps.status_code == 200, apps.text
        # Sourcing: refused on the same tier.
        assert client.post(f"/api/v1/employer/jobs/{job['job_id']}/candidates",
                           headers=employer_account["headers"], json={}).status_code == 402

    def test_seeing_your_own_standing_is_never_sold(
        self, client, employer_account, register, stub_embedder, limits_on
    ) -> None:
        """Knowing where you stand must not be purchasable.

        It was briefly gated behind Prism. Score and ordering were identical
        either way, so it looked fair — but a candidate who knows they are 14th
        of 62, and which claimed skill costs them, can act where one who does
        not know cannot. That is advantage bought with money, on the side of the
        market with the least of it. Runs with limits ENFORCED, because that is
        the configuration in which a paywall would reappear.
        """
        job = _job(client, employer_account["headers"])
        seeker = register(client, "seeker")
        client.post("/api/v1/seeker/profile", headers=seeker["headers"], json={
            "full_name": "Pelamar", "region_code": "3171", "skills": ["Kasir"]})
        assert client.post("/api/v1/seeker/apply", headers=seeker["headers"],
                           json={"job_id": job["job_id"]}).status_code == 201
        app_id = client.get("/api/v1/seeker/applications",
                            headers=seeker["headers"]).json()[0]["application_id"]

        resp = client.get(f"/api/v1/seeker/applications/{app_id}/rank",
                          headers=seeker["headers"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["rank"] == 1

    def test_the_rank_payload_answers_why_not_just_where(
        self, client, employer_account, register, stub_embedder
    ) -> None:
        """A bare position is a scoreboard; the point is the route upward.

        Runs with limits off (conftest default), so this exercises the feature
        itself rather than the gate — the gate is covered above.
        """
        job = _job(client, employer_account["headers"])
        seeker = register(client, "seeker")
        client.post("/api/v1/seeker/profile", headers=seeker["headers"], json={
            "full_name": "Pelamar", "region_code": "3171", "skills": ["Kasir"]})
        client.post("/api/v1/seeker/apply", headers=seeker["headers"],
                    json={"job_id": job["job_id"]})
        app_id = client.get("/api/v1/seeker/applications",
                            headers=seeker["headers"]).json()[0]["application_id"]

        body = client.get(f"/api/v1/seeker/applications/{app_id}/rank",
                          headers=seeker["headers"]).json()
        assert body["rank"] == 1 and body["total_applicants"] == 1
        # Too small a field to quote a percentile honestly.
        assert body["percentile"] is None
        assert "how_to_improve" in body and body["how_to_improve"]

    def test_another_seeker_cannot_probe_an_application_id(
        self, client, employer_account, register, stub_embedder, limits_on
    ) -> None:
        """Ownership is checked BEFORE entitlement: a 402 on someone else's
        application would confirm that the id exists."""
        job = _job(client, employer_account["headers"])
        owner = register(client, "seeker")
        client.post("/api/v1/seeker/profile", headers=owner["headers"], json={
            "full_name": "Pemilik", "region_code": "3171", "skills": ["Kasir"]})
        assert client.post("/api/v1/seeker/apply", headers=owner["headers"],
                           json={"job_id": job["job_id"]}).status_code == 201
        app_id = client.get("/api/v1/seeker/applications",
                            headers=owner["headers"]).json()[0]["application_id"]

        stranger = register(client, "seeker")
        client.post("/api/v1/seeker/profile", headers=stranger["headers"], json={
            "full_name": "Orang Lain", "region_code": "3171", "skills": ["Kasir"]})
        assert client.get(f"/api/v1/seeker/applications/{app_id}/rank",
                          headers=stranger["headers"]).status_code == 404

    def test_paying_reveals_the_position_without_changing_it(
        self, client, employer_account, register, stub_embedder
    ) -> None:
        """Prism buys visibility, never movement — the rank it reports is the
        same ordering every tier already gets."""
        from backend.app.services.matching.application_rank import _rank_of

        scores = [0.9, 0.7, 0.7, 0.4]
        assert _rank_of(0.9, scores) == 1
        # Ties share a rank rather than being broken arbitrarily.
        assert _rank_of(0.7, scores) == 2
        assert _rank_of(0.4, scores) == 4

    def test_talent_search_is_anonymised(self, client, employer_account, register,
                                         stub_embedder) -> None:
        job = _job(client, employer_account["headers"])
        seeker = register(client, "seeker")
        client.post("/api/v1/seeker/profile", headers=seeker["headers"], json={
            "full_name": "Nama Asli", "region_code": "3171", "skills": ["Kasir"],
            "experience": [{"company": "PT Rahasia", "title": "Kasir", "start_date": "2022-01"}]})
        cands = client.post(f"/api/v1/employer/jobs/{job['job_id']}/candidates",
                            headers=employer_account["headers"], json={}).json()["candidates"]
        assert cands and all("Nama Asli" not in str(c) and "Rahasia" not in str(c) for c in cands)
