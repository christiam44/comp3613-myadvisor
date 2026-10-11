from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models.myadvisor import AcademicRecord, Course, CoursePlan, DegreeProgram, SemesterPlan
from app.models.user import User


class MyAdvisorRepository:
    def __init__(self, db: Session):
        self.db = db

    def ensure_program_and_courses(self) -> None:
        if not self.db.exec(select(DegreeProgram)).first():
            program = DegreeProgram(name="Computer Science", required_credits=93)
            self.db.add(program)
            self.db.commit()

        course_seed = [
            ("COMP 101", "Intro to Computing", 3, "Core"),
            ("MATH 220", "Discrete Mathematics", 3, "Core"),
            ("ENG 202", "Technical Writing", 3, "Elective"),
            ("COMP 210", "Data Structures", 3, "Core"),
            ("BIO 150", "Biology Fundamentals", 3, "Elective"),
            ("STAT 210", "Statistics for Science", 3, "Core"),
            ("COMP 215", "Software Design", 4, "Core"),
            ("COMP 230", "Computer Architecture", 4, "Core"),
            ("MATH 230", "Linear Algebra", 4, "Core"),
            ("PHYS 201", "Physics I", 5, "Elective"),
            ("COMP 310", "Algorithms", 4, "Core"),
            ("COMP 320", "Operating Systems", 4, "Core"),
            ("COMP 330", "Database Systems", 4, "Core"),
            ("ENG 310", "Professional Communication", 3, "Elective"),
            ("STAT 310", "Applied Regression", 4, "Core"),
            ("PSY 101", "Intro to Psychology", 3, "Elective"),
            ("CHEM 110", "General Chemistry", 5, "Elective"),
            ("COMP 410", "Distributed Systems", 6, "Elective"),
            ("MATH 350", "Probability and Statistics", 4, "Core"),
            ("COMP 420", "Human-Computer Interaction", 3, "Elective"),
        ]
        for code, title, credits, kind in course_seed:
            if not self.db.exec(select(Course).where(Course.course_code == code)).first():
                self.db.add(Course(course_code=code, title=title, credits=credits, level="200", description=f"{kind} course"))
        self.db.commit()

    def get_courses(self):
        return self.db.exec(select(Course).order_by(Course.course_code)).all()

    def get_course_by_code(self, code: str) -> Optional[Course]:
        return self.db.exec(select(Course).where(Course.course_code == code)).one_or_none()

    def get_course_by_id(self, course_id: int) -> Optional[Course]:
        return self.db.get(Course, course_id)

    def get_latest_plan_for_student(self, student_id: int) -> Optional[SemesterPlan]:
        return self.db.exec(
            select(SemesterPlan)
            .where(SemesterPlan.student_id == student_id)
            .order_by(SemesterPlan.id.desc())
        ).first()

    def get_plan_by_id(self, plan_id: int) -> Optional[SemesterPlan]:
        return self.db.get(SemesterPlan, plan_id)

    def get_course_plan_entries(self, semester_plan_id: int):
        return self.db.exec(
            select(CoursePlan)
            .where(CoursePlan.semester_plan_id == semester_plan_id)
            .order_by(CoursePlan.id)
        ).all()

    def get_course_plan_course_ids(self, semester_plan_id: int):
        return [item.course_id for item in self.get_course_plan_entries(semester_plan_id)]

    def get_courses_for_plan(self, semester_plan_id: int):
        entries = self.get_course_plan_entries(semester_plan_id)
        course_ids = [entry.course_id for entry in entries]
        if not course_ids:
            return []
        return self.db.exec(select(Course).where(Course.id.in_(course_ids)).order_by(Course.course_code)).all()

    def create_plan(self, student_id: int, semester: str, selected_course_codes: list[str]) -> SemesterPlan:
        plan = SemesterPlan(
            student_id=student_id,
            semester=semester,
            status="pending",
            advising_session_notes="",
            submitted_at=datetime.utcnow().strftime("%Y-%m-%d"),
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        for code in selected_course_codes:
            course = self.get_course_by_code(code)
            if course is None:
                continue
            item = CoursePlan(semester_plan_id=plan.id, course_id=course.id)
            self.db.add(item)
        self.db.commit()
        return plan

    def get_pending_plans(self):
        return self.db.exec(
            select(SemesterPlan)
            .where(SemesterPlan.status == "pending")
            .order_by(SemesterPlan.id.desc())
        ).all()

    def get_pending_plan_summaries(self):
        plans = self.get_pending_plans()
        summaries = []
        for plan in plans:
            student = self.db.get(User, plan.student_id)
            course_entries = self.get_courses_for_plan(plan.id)
            summaries.append({
                "plan": plan,
                "student": student,
                "courses": course_entries,
                "total_credits": sum(course.credits for course in course_entries),
            })
        return summaries

    def request_changes(self, plan_id: int, notes: str, advisor_id: int) -> SemesterPlan:
        plan = self.get_plan_by_id(plan_id)
        if plan is None:
            raise ValueError("Plan not found")
        plan.status = "flagged_for_changes"
        plan.advising_session_notes = notes
        plan.advisor_id = advisor_id
        plan.review_date = datetime.utcnow().strftime("%Y-%m-%d")
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def approve_plan(self, plan_id: int, notes: str, advisor_id: int) -> SemesterPlan:
        plan = self.get_plan_by_id(plan_id)
        if plan is None:
            raise ValueError("Plan not found")
        plan.status = "approved"
        plan.advising_session_notes = notes
        plan.advisor_id = advisor_id
        plan.review_date = datetime.utcnow().strftime("%Y-%m-%d")
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_student_progress(self, student_id: int):
        return self.db.exec(
            select(AcademicRecord).where(AcademicRecord.student_id == student_id).order_by(AcademicRecord.id)
        ).all()

    def get_student_academic_records(self, student_id: int):
        return self.db.exec(
            select(AcademicRecord)
            .where(AcademicRecord.student_id == student_id)
            .order_by(AcademicRecord.semester, AcademicRecord.id)
        ).all()

    def upsert_plan_courses_as_in_progress(self, semester_plan_id: int) -> list[AcademicRecord]:
        plan = self.get_plan_by_id(semester_plan_id)
        if plan is None:
            return []

        records: list[AcademicRecord] = []
        for course in self.get_courses_for_plan(semester_plan_id):
            existing = self.db.exec(
                select(AcademicRecord)
                .where(
                    AcademicRecord.student_id == plan.student_id,
                    AcademicRecord.course_id == course.id,
                    AcademicRecord.semester == plan.semester,
                )
            ).first()

            if existing is None:
                existing = AcademicRecord(
                    student_id=plan.student_id,
                    course_id=course.id,
                    semester=plan.semester,
                    grade=None,
                    status="in_progress",
                )
                self.db.add(existing)
                self.db.commit()
                self.db.refresh(existing)
                records.append(existing)
                continue

            if existing.status == "completed" and existing.semester != plan.semester:
                records.append(existing)
                continue

            existing.status = "in_progress"
            existing.grade = None
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            records.append(existing)

        return records

    def upsert_student_course_status(self, student_id: int, course_code: str, semester: str, status: str, grade: Optional[str] = None):
        course = self.get_course_by_code(course_code)
        if course is None:
            raise ValueError("Course not found")

        record = self.db.exec(
            select(AcademicRecord)
            .where(
                AcademicRecord.student_id == student_id,
                AcademicRecord.course_id == course.id,
                AcademicRecord.semester == semester,
            )
        ).first()

        if record is None:
            record = AcademicRecord(
                student_id=student_id,
                course_id=course.id,
                semester=semester,
                status=status,
                grade=grade,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record

        record.status = status
        record.grade = grade
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_completed_credits_for_student(self, student_id: int) -> int:
        records = self.db.exec(
            select(AcademicRecord)
            .where(AcademicRecord.student_id == student_id, AcademicRecord.status == "completed")
        ).all()
        total = 0
        for record in records:
            course = self.get_course_by_id(record.course_id)
            if course is not None:
                total += course.credits
        return total
