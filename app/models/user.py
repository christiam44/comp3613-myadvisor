from sqlmodel import Field, SQLModel
from typing import Optional
from pydantic import EmailStr


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    password: str
    role: str = "student"
    first_name: str = ""
    last_name: str = ""
    student_id: Optional[str] = None
    major: str = "Computer Science"
    enrollment_type: str = "Full-time"
    degree_program_id: Optional[int] = Field(default=None, foreign_key="degreeprogram.id")


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)