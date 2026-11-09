from typing import Optional

from fastapi import HTTPException, Query, status
from pydantic import BaseModel

from . import api_router
from app.dependencies.session import SessionDep
from app.dependencies.auth import AdminDep, StudentDep
from app.repositories.user import UserRepository
from app.repositories.myadvisor import MyAdvisorRepository
from app.services.auth_service import AuthService
from app.services.myadvisor_service import MyAdvisorService


class LoginIn(BaseModel):
    username: str
    password: str


class PlanIn(BaseModel):
    course_codes: list[str]


class ReviewIn(BaseModel):
    decision: str  # "approved" | "flagged_for_changes"
    notes: str


class RecordIn(BaseModel):
    status: str  # "in_progress" | "completed"
    grade: Optional[str] = None
    semester: Optional[str] = None


def _service(db) -> MyAdvisorService:
    service = MyAdvisorService(MyAdvisorRepository(db))
    service.ensure_seed_data()
    return service


def _plan_payload(service: MyAdvisorService, plan) -> dict:
    courses = service.repo.get_courses_for_plan(plan.id)
    return {
        "id": plan.id,
        "student_id": plan.student_id,
        "semester": plan.semester,
        "status": plan.status,
        "advising_session_notes": plan.advising_session_notes,
        "advisor_id": plan.advisor_id,
        "review_date": plan.review_date,
        "submitted_at": plan.submitted_at,
        "course_codes": [c.course_code for c in courses],
        "total_credits": sum(c.credits for c in courses),
    }


@api_router.post("/login")
async def api_login(body: LoginIn, db: SessionDep):
    token = AuthService(UserRepository(db)).authenticate_user(body.username, body.password)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    return {"access_token": token, "token_type": "bearer"}


@api_router.get("/courses")
async def api_list_courses(db: SessionDep, user: StudentDep, q: str = Query(default="")):
    term = q.strip().lower()
    courses = _service(db).list_courses()
    return [
        {"course_code": c.course_code, "title": c.title, "credits": c.credits}
        for c in courses
        if not term or term in c.course_code.lower() or term in c.title.lower()
    ]


@api_router.post("/plans", status_code=status.HTTP_201_CREATED)
async def api_submit_plan(body: PlanIn, db: SessionDep, user: StudentDep):
    service = _service(db)
    try:
        plan = service.submit_plan(user.id, body.course_codes)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return _plan_payload(service, plan)


@api_router.get("/plans/mine")
async def api_my_plan(db: SessionDep, user: StudentDep):
    service = _service(db)
    plan = service.repo.get_latest_plan_for_student(user.id)
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No plan submitted yet")
    return _plan_payload(service, plan)


@api_router.get("/plans")
async def api_list_plans(db: SessionDep, user: AdminDep, plan_status: str = Query(default="pending", alias="status")):
    if plan_status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only status=pending is supported")
    rows = []
    for entry in _service(db).get_pending_plans():
        student, plan = entry["student"], entry["plan"]
        rows.append({
            "id": plan.id,
            "student_username": student.username,
            "student_name": f"{student.first_name} {student.last_name}".strip() or student.username,
            "major": student.major,
            "enrollment_type": student.enrollment_type,
            "submitted_at": plan.submitted_at,
            "total_credits": entry["total_credits"],
            "course_codes": [c.course_code for c in entry["courses"]],
        })
    return rows


@api_router.put("/plans/{plan_id}/review")
async def api_review_plan(plan_id: int, body: ReviewIn, db: SessionDep, advisor: AdminDep):
    service = _service(db)
    try:
        plan = service.review_plan(plan_id, body.decision, body.notes, advisor.id)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return _plan_payload(service, plan)


@api_router.get("/progress")
async def api_progress(db: SessionDep, user: StudentDep):
    return _service(db).get_progress_summary(user.id)


@api_router.put("/records/{course_code}")
async def api_update_record(course_code: str, body: RecordIn, db: SessionDep, user: StudentDep):
    service = _service(db)
    kwargs = {"semester": body.semester} if body.semester else {}
    try:
        record = service.set_course_status(user.id, course_code, body.status, body.grade, **kwargs)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"course_code": course_code, "semester": record.semester, "status": record.status, "grade": record.grade}