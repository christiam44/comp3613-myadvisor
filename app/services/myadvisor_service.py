from typing import Any

from app.repositories.myadvisor import MyAdvisorRepository


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
