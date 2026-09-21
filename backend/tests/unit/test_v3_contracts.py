"""Guards for the v3 invariants — each one encodes a defect we actually shipped.

Every test here exists because the property it checks was silently false in
production code, not because it seemed like a good idea.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.services.billing import plans
from backend.app.services.quiz import service
from backend.app.services.trust import rules


class _Q:
    def __init__(self, qid: str) -> None:
        self.id = qid


class _Attempt:
    def __init__(self, qids: list[str], when: datetime) -> None:
        self.question_ids = qids
        self.submitted_at = when


class TestRetakeNeverRepeatsTheLastQuiz:
    """The defect: a 6-question bank drawing 5 repeated >=4 on every retake.

    A badge obtainable by memorising six items was feeding a 0.85 proof weight,
    and the only thing slowing it down was a cooldown that was also for sale.
    """

    def _bank(self, n: int) -> list[_Q]:
        return [_Q(f"q{i}") for i in range(n)]

    def test_no_question_from_the_previous_attempt_is_redrawn(self) -> None:
        bank = self._bank(30)
        now = datetime.now(UTC)
        first = service._pick_questions(bank, [])
        attempt = _Attempt([q.id for q in first], now)

        for _ in range(25):
            second = service._pick_questions(bank, [attempt])
            assert not ({q.id for q in second} & set(attempt.question_ids)), (
                "a retake redrew a question the candidate just saw"
            )

    def test_a_thin_bank_still_serves_rather_than_locking_the_candidate_out(self) -> None:
        """Our unfinished bank must never become the candidate's punishment."""
        bank = self._bank(6)
        attempt = _Attempt([q.id for q in bank[:5]], datetime.now(UTC))
        picked = service._pick_questions(bank, [attempt])
        assert len(picked) == service.QUESTIONS_PER_QUIZ

    def test_two_attempts_back_are_avoided_when_the_bank_allows(self) -> None:
        bank = self._bank(30)
        now = datetime.now(UTC)
        older = _Attempt([f"q{i}" for i in range(5)], now - timedelta(days=2))
        recent = _Attempt([f"q{i}" for i in range(5, 10)], now - timedelta(days=1))
        seen = set(older.question_ids) | set(recent.question_ids)
        for _ in range(25):
            picked = service._pick_questions(bank, [older, recent])
            assert not ({q.id for q in picked} & seen)


class TestPayingNeverBuysProofOrLessService:
    def test_the_retake_cooldown_is_the_same_for_everyone(self) -> None:
        """Prism used to cut the cooldown 7 days -> 2.

        That is money shortening the path to a badge, and a badge moves the match
        score — the single thing the product promises paying cannot do.
        """
        assert not hasattr(service, "RETAKE_DAYS_PRISM")
        assert service.RETAKE_DAYS == 1

    def test_the_paid_advisor_quota_is_larger_on_the_same_axis(self) -> None:
        """The defect: 10/day free versus 100/30 days paid.

        Free was 300 a month, Prism was 100, and an exhausted Prism user waited
        up to 30 days where a free user waited until tomorrow. Paying bought
        less service and a longer lockout.
        """
        assert not hasattr(plans, "ADVISOR_PRISM_PER_30_DAYS"), (
            "a per-30-day paid quota cannot be compared with a per-day free one"
        )
        assert plans.ADVISOR_PRISM_PER_DAY > plans.ADVISOR_FREE_PER_DAY

    def test_ranked_applicants_are_not_capped_by_default(self) -> None:
        """Ranking costs Rp0 to compute, so capping it only hid candidates."""
        from backend.app.config.settings import settings

        assert settings.spark_ranked_applicant_limit == 0

    def test_quota_sits_on_reverse_matching_instead(self) -> None:
        ent = plans.Entitlements()
        assert plans.talent_search_limit(ent) == 0
        ent.beacon_jobs.add("job-1")
        assert plans.talent_search_limit(ent) > 0


class TestReportsCannotRemoveAPostingOnTheirOwn:
    def test_a_brand_new_unverified_account_carries_no_weight(self) -> None:
        assert (
            rules.reporter_weight(
                email_verified=False,
                applied_to_job=False,
                account_age_days=0,
                upheld_reports=0,
                dismissed_reports=0,
            )
            == 0
        )

    def test_a_serial_false_reporter_stops_counting(self) -> None:
        assert (
            rules.reporter_weight(
                email_verified=True,
                applied_to_job=True,
                account_age_days=400,
                upheld_reports=0,
                dismissed_reports=rules.DISMISSED_REPORTS_TO_MUTE,
            )
            == 0
        )

    def test_reaching_the_threshold_flags_rather_than_hides(self) -> None:
        assert rules.flag_state(rules.FLAG_WEIGHT_THRESHOLD, reports=3) == "flagged"
        assert "flagged" in __import__(
            "backend.app.services.trust.policy", fromlist=["policy"]
        ).VISIBLE_STATUSES, "a flagged posting must stay readable while it is reviewed"

    def test_one_loud_reporter_is_not_enough(self) -> None:
        """Weight alone must not trip the flag — it takes more than one person."""
        assert rules.flag_state(99, reports=1) == "published"


class TestRejectionMustCarryAReason:
    def test_the_catalogue_is_closed_and_non_empty(self) -> None:
        from backend.app.api.routers.employer import REJECTION_REASONS

        assert REJECTION_REASONS
        assert "lainnya" in REJECTION_REASONS

    @pytest.mark.parametrize("code", ["", "tidak_suka", "NOPE"])
    def test_unknown_codes_are_not_accepted(self, code: str) -> None:
        from backend.app.api.routers.employer import REJECTION_REASONS

        assert code not in REJECTION_REASONS


class TestGeneratedQuestionsAreScreened:
    def test_a_giveaway_answer_is_rejected(self) -> None:
        from backend.app.services.quiz.generator import validate_question

        problem = validate_question(
            "Pelanggan komplain karena pesanannya terlambat. Apa langkah pertama?",
            ["Diam saja", "Marah", "Minta maaf", "x" * 200],
            3,
        )
        assert problem is not None

    def test_combination_options_are_rejected(self) -> None:
        from backend.app.services.quiz.generator import validate_question

        problem = validate_question(
            "Pelanggan komplain karena pesanannya terlambat. Apa langkah pertama?",
            ["Minta maaf", "Cek pesanan", "Semua benar", "Abaikan"],
            0,
        )
        assert problem is not None

    def test_a_sound_question_passes(self) -> None:
        from backend.app.services.quiz.generator import validate_question

        assert (
            validate_question(
                "Pelanggan komplain karena pesanannya terlambat. Apa langkah pertama?",
                ["Minta maaf dan cek status", "Abaikan", "Minta dia telepon", "Tutup chat"],
                0,
            )
            is None
        )
