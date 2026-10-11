"""Database table models.

Import every table model here so ``SQLModel.metadata.create_all`` sees them.
"""

from app.models.user import User
from app.models.myadvisor import (
    AcademicRecord,
    Course,
    CoursePlan,
    DegreeProgram,
    DegreeRequirement,
    Prerequisite,
    SemesterPlan,
)

__all__ = [
    "User",
    "AcademicRecord",
    "Course",
    "CoursePlan",
    "DegreeProgram",
    "DegreeRequirement",
    "Prerequisite",
    "SemesterPlan",
]
