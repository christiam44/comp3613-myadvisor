import pytest

from app.models.myadvisor import AcademicRecord
from app.repositories.myadvisor import MyAdvisorRepository


@pytest.fixture
def repo(db, seeded):
    return MyAdvisorRepository(db)


def test_seed_creates_courses_and_program(repo):
    assert len(repo.get_courses()) == 20


def test_seed_is_idempotent(repo):
    repo.ensure_program_and_courses()
    assert len(repo.get_courses()) == 20


def test_create_plan_skips_unknown_codes(repo, student):
    plan = repo.create_plan(student.id, "Fall 2026", ["COMP 101", "FAKE 999"])
    assert len(repo.get_courses_for_plan(plan.id)) == 1


def test_new_plan_is_pending_with_submission_date(repo, student):
    plan = repo.create_plan(student.id, "Fall 2026", ["COMP 101"])
    assert plan.status == "pending"
    assert plan.submitted_at is not None


def test_pending_plans_exclude_reviewed(repo, student, advisor):
    p1 = repo.create_plan(student.id, "Fall 2026", ["COMP 101"])
    repo.create_plan(student.id, "Fall 2026", ["MATH 220"])
    repo.approve_plan(p1.id, "ok", advisor.id)
    pending = repo.get_pending_plans()
    assert len(pending) == 1
    assert pending[0].id != p1.id


def test_latest_plan_for_student_returns_newest(repo, student):
    repo.create_plan(student.id, "Fall 2026", ["COMP 101"])
    second = repo.create_plan(student.id, "Fall 2026", ["MATH 220"])
    assert repo.get_latest_plan_for_student(student.id).id == second.id


def test_request_changes_sets_status_and_notes(repo, student, advisor):
    plan = repo.create_plan(student.id, "Fall 2026", ["COMP 101"])
    updated = repo.request_changes(plan.id, "Swap a course", advisor.id)
    assert updated.status == "flagged_for_changes"
    assert updated.advising_session_notes == "Swap a course"
    assert updated.advisor_id == advisor.id


def test_approve_unknown_plan_raises(repo, advisor):
    with pytest.raises(ValueError):
        repo.approve_plan(999, "ok", advisor.id)


def test_completed_credits_sums_only_completed(repo, student):
    repo.upsert_student_course_status(student.id, "COMP 101", "Fall 2026", "completed", "A")   # 3 cr
    repo.upsert_student_course_status(student.id, "COMP 215", "Fall 2026", "completed", "B")   # 4 cr
    repo.upsert_student_course_status(student.id, "MATH 220", "Fall 2026", "in_progress")      # ignored
    assert repo.get_completed_credits_for_student(student.id) == 7


def test_upsert_status_updates_existing_record(repo, student):
    repo.upsert_student_course_status(student.id, "COMP 101", "Fall 2026", "in_progress")
    record = repo.upsert_student_course_status(student.id, "COMP 101", "Fall 2026", "completed", "A")
    assert record.status == "completed"
    assert len(repo.get_student_academic_records(student.id)) == 1


def test_upsert_status_unknown_course_raises(repo, student):
    with pytest.raises(ValueError):
        repo.upsert_student_course_status(student.id, "FAKE 999", "Fall 2026", "completed")


def test_approval_creates_in_progress_records(repo, student, advisor):
    plan = repo.create_plan(student.id, "Fall 2026", ["COMP 101", "MATH 220"])
    repo.approve_plan(plan.id, "ok", advisor.id)
    records = repo.upsert_plan_courses_as_in_progress(plan.id)
    assert len(records) == 2
    assert all(r.status == "in_progress" for r in records)