"""Email OTP — the only identity check KerjaCerdas runs in-house.

NIK / KTP / ijazah / NPWP flows were removed (UU PDP data minimisation):
these tests also pin that those endpoints no longer exist.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.config.settings import settings


def _send(client: TestClient, headers: dict) -> dict:
    resp = client.post("/api/v1/verify/email/send", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestEmailOtp:
    def test_send_requires_authentication(self, client: TestClient) -> None:
        assert client.post("/api/v1/verify/email/send").status_code == 401

    def test_happy_path_marks_account_verified(self, client: TestClient, seeker_account: dict) -> None:
        h = seeker_account["headers"]
        body = _send(client, h)
        assert body["mode"] == "demo" and len(body["demo_code"]) == 6
        ok = client.post("/api/v1/verify/email/verify", json={"code": body["demo_code"]}, headers=h)
        assert ok.status_code == 200 and ok.json()["email_verified"] is True
        status = client.get("/api/v1/verify/status", headers=h).json()
        assert status["email_verified"] is True

    def test_wrong_code_counts_down(self, client: TestClient, seeker_account: dict) -> None:
        h = seeker_account["headers"]
        code = _send(client, h)["demo_code"]
        wrong = "000000" if code != "000000" else "111111"
        resp = client.post("/api/v1/verify/email/verify", json={"code": wrong}, headers=h)
        assert resp.status_code == 400 and "4 percobaan" in resp.json()["detail"]

    def test_attempts_are_capped(self, client: TestClient, seeker_account: dict) -> None:
        h = seeker_account["headers"]
        code = _send(client, h)["demo_code"]
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            client.post("/api/v1/verify/email/verify", json={"code": wrong}, headers=h)
        last = client.post("/api/v1/verify/email/verify", json={"code": code}, headers=h)
        assert last.status_code in (404, 429)

    def test_code_is_scoped_to_the_requesting_user(
        self, client: TestClient, seeker_account: dict, other_seeker_account: dict
    ) -> None:
        code = _send(client, seeker_account["headers"])["demo_code"]
        resp = client.post(
            "/api/v1/verify/email/verify", json={"code": code}, headers=other_seeker_account["headers"]
        )
        assert resp.status_code == 404

    def test_resend_invalidates_previous_code(self, client: TestClient, seeker_account: dict) -> None:
        h = seeker_account["headers"]
        first = _send(client, h)["demo_code"]
        second = _send(client, h)["demo_code"]
        if first != second:
            assert client.post("/api/v1/verify/email/verify", json={"code": first},
                               headers=h).status_code == 400

    def test_production_without_email_provider_fails_closed(
        self, client: TestClient, seeker_account: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "otp_demo_mode", False)
        monkeypatch.setattr(settings, "resend_api_key", "")
        resp = client.post("/api/v1/verify/email/send", headers=seeker_account["headers"])
        assert resp.status_code == 503
        assert "demo_code" not in resp.text


class TestIdentityDocumentsRemoved:
    @pytest.mark.parametrize("path", ["/api/v1/verify/identity", "/api/v1/verify/education",
                                      "/api/v1/verify/npwp", "/api/v1/verify/otp/send"])
    def test_endpoint_is_gone(self, client: TestClient, seeker_account: dict, path: str) -> None:
        resp = client.post(path, json={}, headers=seeker_account["headers"])
        assert resp.status_code in (404, 405)

    def test_seeker_schema_has_no_nik(self) -> None:
        from backend.app.db.schemas import Employer, SeekerProfile

        assert "nik" not in SeekerProfile.model_fields
        assert "npwp" not in Employer.model_fields
