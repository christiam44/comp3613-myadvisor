from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class DegreeProgram(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    required_credits: int = 0


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_code: str = Field(index=True, unique=True)
    level: str = "100"
    title: str
    description: str = ""
    credits: int = 3


class DegreeRequirement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    degree_program_id: int = Field(foreign_key="degreeprogram.id")
    course_id: int = Field(foreign_key="course.id")
    course_type: str = "required"


class Prerequisite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id")
    prereq_course_id: int = Field(foreign_key="course.id")


class AcademicRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    course_id: int = Field(foreign_key="course.id")
    semester: str
    grade: Optional[str] = None
    status: str = "completed"


class SemesterPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    semester: str
    status: str = "pending"
    advising_session_notes: str = ""
    advisor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    review_date: Optional[str] = None
    submitted_at: Optional[str] = None


class CoursePlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    semester_plan_id: int = Field(foreign_key="semesterplan.id")
    course_id: int = Field(foreign_key="course.id")
