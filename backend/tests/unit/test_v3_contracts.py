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


class TestReviewFindingsStayFixed:
    """One guard per defect found in review of PR #29. Each was live in the branch."""

    def test_only_a_hard_rule_can_hide_a_live_posting(self) -> None:
        """A soft-rule "violation" is an opinion needing context the text lacks.

        The reviewer returned {"verdict": "violation"} for any rule and the
        caller hid the posting, so a model's reading of tone or intent could
        remove a real employer's advert unattended.
        """
        import inspect

        from backend.app.api.routers import public_jobs

        src = inspect.getsource(public_jobs.report_job)
        assert 'review.get("severity") == "hard"' in src

    def test_the_reviewer_reports_severity_at_all(self) -> None:
        import inspect

        from backend.app.services.trust import automod

        src = inspect.getsource(automod.review_reported_posting)
        assert '"severity"' in src

    def test_a_report_must_cite_a_rule(self) -> None:
        """An uncitable report cannot be checked, yet still moved the threshold."""
        import pytest as _pytest
        from pydantic import ValidationError

        from backend.app.api.routers.public_jobs import ReportReq

        with _pytest.raises(ValidationError):
            ReportReq(reason="palsu")
        assert ReportReq(reason="palsu", rule_cited="R1").rule_cited == "R1"

    def test_the_rulebook_route_is_declared_before_the_code_catch_all(self) -> None:
        """/rules was shadowed by /{code} and resolved as a job code lookup."""
        import inspect

        from backend.app.api.routers import public_jobs

        src = inspect.getsource(public_jobs)
        assert src.index('@router.get("/rules")') < src.index('@router.get("/{code}")')

    def test_a_cold_bank_is_throttled_too(self) -> None:
        """Exempting cold banks left the paid generator open to hammering."""
        from backend.app.services.quiz import service as svc

        svc._last_topup.pop("throttle-probe", None)
        assert svc._topup_allowed("throttle-probe", serveable=False) is True
        assert svc._topup_allowed("throttle-probe", serveable=False) is False
        svc._last_topup.pop("throttle-probe", None)

    def test_a_thin_bank_repeats_the_stalest_questions_not_random_ones(self) -> None:
        """When the rule cannot be honoured, overlap must be minimised, not luck."""
        bank = [_Q(f"q{i}") for i in range(6)]
        now = datetime.now(UTC)
        oldest = _Attempt(["q0", "q1"], now - timedelta(days=9))
        newest = _Attempt(["q2", "q3", "q4", "q5", "q0"], now - timedelta(days=1))

        picked = {q.id for q in service._pick_questions(bank, [oldest, newest])}
        assert len(picked) == service.QUESTIONS_PER_QUIZ
        # q1 is the only question absent from the most recent attempt, so it must
        # always be drawn; the remainder comes from the least-recently-seen end.
        assert "q1" in picked

    def test_the_interview_kit_reports_a_miss_on_the_first_call(self) -> None:
        """`key in cache` was evaluated after the insert, so every call said hit."""
        import inspect

        from backend.app.api.routers import hiring

        src = inspect.getsource(hiring.interview_kit)
        assert "was_cached" in src
        assert '"cached": key in _KIT_CACHE' not in src

    def test_an_admin_decision_records_whether_reports_held_up(self) -> None:
        """Nothing wrote `upheld`, so every reporter's history was permanently empty."""
        import inspect

        from backend.app.api.routers import admin

        src = inspect.getsource(admin.moderate_job)
        assert "r.upheld" in src

    def test_reporter_standing_is_mapped_from_seeker_to_user_ids(self) -> None:
        """Applications hold seeker-profile ids; reports hold user ids."""
        import inspect

        from backend.app.api.routers import public_jobs

        src = inspect.getsource(public_jobs._weighted_report_score)
        assert "applicant_user_ids" in src
        assert "seekers.get_many" in src


class TestSecondReviewFindingsStayFixed:
    """Round two. Two new defects, plus four the first fix did not fully close."""

    def test_an_admin_decision_never_rewrites_a_settled_verdict(self) -> None:
        """find_reports_for_job returns EVERY report, resolved ones included.

        Writing `upheld` to all of them let a June dismissal silently mark a
        March complaint wrong. Standing must be a record, not a copy of the most
        recent decision on the same posting.
        """
        import inspect

        from backend.app.api.routers import admin

        src = inspect.getsource(admin.moderate_job)
        assert "if r.resolved:" in src and "continue" in src

    def test_the_flagged_state_is_visible_to_the_admins_who_resolve_it(self) -> None:
        """A flagged posting that no admin can see means reports never resolve,
        which is why reporter history stayed empty even after it was writable."""
        import inspect

        from backend.app.api.routers import admin

        src = inspect.getsource(admin.moderation_queue)
        assert '"flagged"' in src and '"held"' in src

    def test_hard_rules_are_evaluated_before_soft_ones(self) -> None:
        """A soft rule returning RAGU used to end the review, so a cited R1 —
        the only rule we act on unattended — was never asked."""
        import inspect

        from backend.app.services.trust import automod

        src = inspect.getsource(automod.review_reported_posting)
        assert 'rules.sort(key=lambda r: 0 if r.severity == "hard" else 1)' in src
        # A soft finding may not return early; it parks in `fallback`.
        assert "fallback = fallback or" in src

    def test_generation_is_budgeted_per_user_not_only_per_skill(self) -> None:
        """Claiming a skill is free and unlimited, so a per-skill throttle alone
        bounds nothing: fifty invented skills buy fifty generations."""
        import inspect

        from backend.app.services.quiz import service as svc

        assert svc.GENERATIONS_PER_USER_PER_DAY > 0
        assert "consume_quota" in inspect.getsource(svc._generation_budget_left)
        # And the budget must actually gate the call site, not merely exist.
        assert "_generation_budget_left" in inspect.getsource(svc.start_quiz)

    def test_a_thin_bank_reports_the_overlap_it_could_not_avoid(self) -> None:
        """A guarantee we cannot keep must be visible, never absorbed quietly."""
        import inspect

        from backend.app.services.quiz import service as svc

        src = inspect.getsource(svc.start_quiz)
        assert "repeated_questions" in src
        assert "needs_refill_now" in src

    def test_plan_figures_are_consistent_everywhere_they_appear(self) -> None:
        """The prices live in settings; no doc or component may carry its own."""
        from pathlib import Path

        from backend.app.config.settings import settings

        root = Path(__file__).resolve().parents[3]
        stale = {"Rp29.000", "Rp99.000", "Rp25.000", "100 pesan"}
        offenders: list[str] = []
        for pattern in ("docs/**/*.md", "frontend/src/**/*.jsx", "README.md"):
            for path in root.glob(pattern):
                text = path.read_text(encoding="utf-8", errors="ignore")
                hits = [s for s in stale if s in text]
                if hits:
                    offenders.append(f"{path.relative_to(root)}: {hits}")
        assert not offenders, "stale plan figures still shipped:\n" + "\n".join(offenders)
        assert settings.plan_price_beacon == 49_000
