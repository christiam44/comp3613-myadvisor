import pytest

from app.repositories.myadvisor import MyAdvisorRepository
from app.services.myadvisor_service import MyAdvisorService


@pytest.fixture
def service(db, seeded):
    return MyAdvisorService(MyAdvisorRepository(db))


def test_submit_plan_sets_pending(service, student):
    plan = service.submit_plan(student.id, ["COMP 101"])
    assert plan.status == "pending"


def test_submit_plan_dedupes_codes(service, student):
    plan = service.submit_plan(student.id, ["COMP 101", "COMP 101"])
    assert len(service.repo.get_courses_for_plan(plan.id)) == 1


def test_submit_plan_empty_raises(service, student):
    with pytest.raises(ValueError):
        service.submit_plan(student.id, [])


def test_review_records_advisor_and_date(service, student, advisor):
    plan = service.submit_plan(student.id, ["COMP 101"])
    reviewed = service.review_plan(plan.id, "approved", "Looks good", advisor.id)
    assert reviewed.advisor_id == advisor.id
    assert reviewed.review_date is not None
    assert reviewed.status == "approved"


def test_only_pending_plans_can_be_reviewed(service, student, advisor):
    plan = service.submit_plan(student.id, ["COMP 101"])
    service.review_plan(plan.id, "approved", "ok", advisor.id)
    with pytest.raises(ValueError):
        service.review_plan(plan.id, "approved", "again", advisor.id)


def test_in_progress_clears_grade(service, student):
    record = service.set_course_status(student.id, "COMP 101", "in_progress", grade="A")
    assert record.grade is None

    def test_review_invalid_decision_raises(service, student, advisor):
    plan = service.submit_plan(student.id, ["COMP 101"])
    with pytest.raises(ValueError):
        service.review_plan(plan.id, "maybe", "notes", advisor.id)


def test_review_blank_notes_raises(service, student, advisor):
    plan = service.submit_plan(student.id, ["COMP 101"])
    with pytest.raises(ValueError):
        service.review_plan(plan.id, "approved", "   ", advisor.id)


def test_review_unknown_plan_raises_lookup(service, advisor):
    with pytest.raises(LookupError):
        service.review_plan(999, "approved", "ok", advisor.id)


def test_submit_unknown_course_raises(service, student):
    with pytest.raises(ValueError):
        service.submit_plan(student.id, ["FAKE 999"])


def test_set_status_invalid_status_raises(service, student):
    with pytest.raises(ValueError):
        service.set_course_status(student.id, "COMP 101", "dropped")


def test_set_status_invalid_grade_raises(service, student):
    with pytest.raises(ValueError):
        service.set_course_status(student.id, "COMP 101", "completed", grade="F")


def test_set_status_unknown_course_raises_lookup(service, student):
    with pytest.raises(LookupError):
        service.set_course_status(student.id, "FAKE 999", "completed", grade="A")


def test_grade_is_normalised_to_uppercase(service, student):
    record = service.set_course_status(student.id, "COMP 101", "completed", grade="b")
    assert record.grade == "B"


def test_progress_summary_counts(service, student):
    service.set_course_status(student.id, "COMP 101", "completed", grade="A")
    service.set_course_status(student.id, "MATH 220", "in_progress")
    summary = service.get_progress_summary(student.id)
    assert summary["completed_credits"] == 3
    assert summary["completed_count"] == 1
    assert summary["in_progress_count"] == 1
    assert summary["required_credits"] == 93