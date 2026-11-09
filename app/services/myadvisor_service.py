from typing import Any

from app.repositories.myadvisor import MyAdvisorRepository

VALID_DECISIONS = {"approved", "flagged_for_changes"}
VALID_GRADES = {"A", "B", "C"}
VALID_RECORD_STATUSES = {"in_progress", "completed"}
DEFAULT_SEMESTER = "Fall 2026"
REQUIRED_CREDITS = 93


class MyAdvisorService:
    def __init__(self, repo: MyAdvisorRepository):
        self.repo = repo

    def ensure_seed_data(self):
        self.repo.ensure_program_and_courses()

    def list_courses(self):
        return self.repo.get_courses()

    def get_course_by_code(self, code: str):
        return self.repo.get_course_by_code(code)

    def get_latest_plan_for_student(self, student_id: int):
        plan = self.repo.get_latest_plan_for_student(student_id)
        if not plan:
            return None
        course_details = self.repo.get_courses_for_plan(plan.id)
        return {
            "plan": plan,
            "courses": course_details,
            "course_ids": [course.id for course in course_details],
            "course_codes": [course.course_code for course in course_details],
        }

    def create_plan_for_student(self, student_id: int, selected_course_codes: list[str]):
        self.ensure_seed_data()
        return self.repo.create_plan(student_id=student_id, semester="Fall 2026", selected_course_codes=selected_course_codes)

    def get_pending_plans(self):
        return self.repo.get_pending_plan_summaries()

    def request_changes(self, plan_id: int, notes: str, advisor_id: int):
        return self.repo.request_changes(plan_id, notes, advisor_id)

    def approve_plan(self, plan_id: int, notes: str, advisor_id: int):
        plan = self.repo.approve_plan(plan_id, notes, advisor_id)
        self.repo.upsert_plan_courses_as_in_progress(plan_id)
        return plan

    def get_student_progress(self, student_id: int):
        return self.repo.get_student_progress(student_id)

    def update_student_course_status(self, student_id: int, course_code: str, semester: str, status: str, grade: str | None = None):
        return self.repo.upsert_student_course_status(student_id, course_code, semester, status, grade)

    def get_completed_credits_for_student(self, student_id: int):
        return self.repo.get_completed_credits_for_student(student_id)

    # ---- Validated operations used by the JSON API ----
    # ValueError -> bad input (HTTP 400); LookupError -> not found (HTTP 404)

    def submit_plan(self, student_id: int, course_codes: list[str]):
        codes = list(dict.fromkeys(c.strip() for c in course_codes if c and c.strip()))
        if not codes:
            raise ValueError("Select at least one course")
        self.ensure_seed_data()
        unknown = [c for c in codes if self.repo.get_course_by_code(c) is None]
        if unknown:
            raise ValueError(f"Unknown course code(s): {', '.join(unknown)}")
        return self.repo.create_plan(student_id=student_id, semester=DEFAULT_SEMESTER, selected_course_codes=codes)

    def review_plan(self, plan_id: int, decision: str, notes: str, advisor_id: int):
        if decision not in VALID_DECISIONS:
            raise ValueError("decision must be 'approved' or 'flagged_for_changes'")
        if not notes or not notes.strip():
            raise ValueError("Feedback notes are required")
        plan = self.repo.get_plan_by_id(plan_id)
        if plan is None:
            raise LookupError("Plan not found")
        if plan.status != "pending":
            raise ValueError("Only pending plans can be reviewed")
        if decision == "approved":
            return self.approve_plan(plan_id, notes.strip(), advisor_id)
        return self.request_changes(plan_id, notes.strip(), advisor_id)

    def set_course_status(self, student_id: int, course_code: str, status: str,
                          grade: str | None = None, semester: str = DEFAULT_SEMESTER):
        if status not in VALID_RECORD_STATUSES:
            raise ValueError("status must be 'in_progress' or 'completed'")
        grade = grade.strip().upper() if grade and grade.strip() else None
        if grade is not None and grade not in VALID_GRADES:
            raise ValueError("grade must be A, B or C")
        if status == "in_progress":
            grade = None
        if self.repo.get_course_by_code(course_code) is None:
            raise LookupError("Course not found")
        return self.repo.upsert_student_course_status(student_id, course_code, semester, status, grade)

    def get_progress_summary(self, student_id: int):
        records = self.repo.get_student_academic_records(student_id)
        items = []
        for r in records:
            course = self.repo.get_course_by_id(r.course_id)
            items.append({
                "course_code": course.course_code if course else None,
                "title": course.title if course else None,
                "credits": course.credits if course else 0,
                "semester": r.semester,
                "status": r.status,
                "grade": r.grade,
            })
        return {
            "completed_credits": self.repo.get_completed_credits_for_student(student_id),
            "required_credits": REQUIRED_CREDITS,
            "completed_count": sum(1 for r in records if r.status == "completed"),
            "in_progress_count": sum(1 for r in records if r.status == "in_progress"),
            "records": items,
        }