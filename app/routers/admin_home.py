from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import status
from app.dependencies.session import SessionDep
from app.dependencies.auth import AdminDep, IsUserLoggedIn, get_current_user, is_admin
from . import router, templates
from app.repositories.myadvisor import MyAdvisorRepository
from app.services.myadvisor_service import MyAdvisorService


@router.get("/admin", response_class=HTMLResponse)
async def admin_home_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    repo = MyAdvisorRepository(db)
    service = MyAdvisorService(repo)
    service.ensure_seed_data()
    plans = service.get_pending_plans()
    plan_rows = []
    for entry in plans:
        student = entry["student"]
        plan = entry["plan"]
        student_name = f"{student.first_name} {student.last_name or ''}".strip() or student.username
        major = getattr(student, "major", None) or "Computer Science"
        enrollment_type = getattr(student, "enrollment_type", None) or "Full-time"
        plan_rows.append({
            "id": plan.id,
            "student_name": student_name,
            "student_username": student.username,
            "student_major": major,
            "student_enrollment_type": enrollment_type,
            "submitted_at": plan.submitted_at or "N/A",
            "total_credits": entry["total_credits"],
            "courses": [
                {
                    "course_code": course.course_code,
                    "title": course.title,
                    "credits": course.credits,
                }
                for course in entry["courses"]
            ],
        })

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "user": user,
            "plans": plans,
            "plan_rows": plan_rows,
            "pending_count": len(plan_rows),
        },
    )


@router.post("/admin/approve-plan")
async def approve_plan(
    request: Request,
    user: AdminDep,
    db: SessionDep,
    plan_id: int = Form(...),
    notes: str = Form(...),
):
    repo = MyAdvisorRepository(db)
    service = MyAdvisorService(repo)
    service.approve_plan(plan_id, notes, user.id)
    return RedirectResponse(url=request.url_for("admin_home_view"), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/request-changes")
async def request_changes(
    request: Request,
    user: AdminDep,
    db: SessionDep,
    plan_id: int = Form(...),
    notes: str = Form(...),
):
    repo = MyAdvisorRepository(db)
    service = MyAdvisorService(repo)
    service.request_changes(plan_id, notes, user.id)
    return RedirectResponse(url=request.url_for("admin_home_view"), status_code=status.HTTP_303_SEE_OTHER)
