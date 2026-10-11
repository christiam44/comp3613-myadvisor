from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import status
from app.dependencies.session import SessionDep
from app.dependencies.auth import AuthDep, IsUserLoggedIn, get_current_user, is_admin
from . import router, templates
from app.repositories.myadvisor import MyAdvisorRepository
from app.services.myadvisor_service import MyAdvisorService


@router.get("/app", response_class=HTMLResponse)
async def user_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    repo = MyAdvisorRepository(db)
    service = MyAdvisorService(repo)
    service.ensure_seed_data()
    courses = service.list_courses()
    plan_info = service.get_latest_plan_for_student(user.id)
    current_plan_course_codes = []
    if plan_info:
        current_plan_course_codes = [course.course_code for course in plan_info["courses"]]

    fallback_course_catalog = [
        {"code": "COMP 101", "title": "Intro to Computing", "credits": 3, "type": "Core", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
        {"code": "MATH 220", "title": "Discrete Mathematics", "credits": 3, "type": "Core", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
        {"code": "STAT 210", "title": "Statistics for Science", "credits": 3, "type": "Core", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
        {"code": "COMP 215", "title": "Software Design", "credits": 4, "type": "Core", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
        {"code": "ENG 202", "title": "Technical Writing", "credits": 3, "type": "Elective", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
        {"code": "COMP 210", "title": "Data Structures", "credits": 3, "type": "Core", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
        {"code": "COMP 230", "title": "Computer Architecture", "credits": 4, "type": "Core", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
        {"code": "MATH 230", "title": "Linear Algebra", "credits": 4, "type": "Core", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
        {"code": "COMP 310", "title": "Algorithms", "credits": 4, "type": "Core", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
        {"code": "COMP 330", "title": "Database Systems", "credits": 4, "type": "Core", "eligible": True, "status": "outstanding", "grade": None, "requirement": None},
    ]

    student_records = repo.get_student_academic_records(user.id)
    student_records_by_course_id = {}
    for record in reversed(student_records):
        student_records_by_course_id.setdefault(record.course_id, record)
    completed_course_ids = {record.course_id for record in student_records if record.status == "completed"}
    approved_course_codes = set()

    course_catalog = [
        {
            "code": course.course_code,
            "title": course.title,
            "credits": course.credits,
            "type": "Core" if course.course_code.startswith("COMP") or course.course_code.startswith("MATH") or course.course_code.startswith("STAT") else "Elective",
            "eligible": True,
            "status": "outstanding",
            "grade": None,
            "requirement": None,
        }
        for course in courses
    ]

    for item in course_catalog:
        course = next((course for course in courses if course.course_code == item["code"]), None)
        if course is None:
            continue

        matching_record = student_records_by_course_id.get(course.id)
        if matching_record and matching_record.status == "completed":
            item["status"] = "completed"
            item["grade"] = matching_record.grade
            continue

        if matching_record and matching_record.status == "in_progress":
            item["status"] = "in_progress"
            item["grade"] = matching_record.grade
            continue

    if not course_catalog:
        course_catalog = fallback_course_catalog

    total_completed_credits = service.get_completed_credits_for_student(user.id)

    if plan_info and plan_info["plan"].status == "approved":
        approved_course_codes = set(plan_info["course_codes"])
        for item in course_catalog:
            course = next((course for course in courses if course.course_code == item["code"]), None)
            if course is None:
                continue
            if item["status"] == "completed":
                continue
            if item["code"] in approved_course_codes and course.id not in completed_course_ids:
                item["status"] = "in_progress"
                item["grade"] = None

    plan_courses = []
    if plan_info:
        completed_course_ids = {record.course_id for record in repo.get_student_academic_records(user.id) if record.status == "completed"}
        for course in plan_info["courses"]:
            course_status = "completed" if course.id in completed_course_ids else "in_progress"
            plan_courses.append({
                "course_code": course.course_code,
                "title": course.title,
                "credits": course.credits,
                "status": course_status,
            })
    else:
        plan_courses = []

    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={
            "user": user,
            "courses": courses,
            "course_catalog": course_catalog,
            "current_plan": plan_info.get("plan") if plan_info else None,
            "current_plan_courses": plan_courses,
            "current_plan_course_codes": current_plan_course_codes,
            "total_completed_credits": total_completed_credits,
            "plan_courses": plan_courses,
        },
    )


@router.post("/app/submit-plan")
async def submit_plan(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    selected_courses: str = Form(...),
):
    repo = MyAdvisorRepository(db)
    service = MyAdvisorService(repo)
    selected_course_codes = [code.strip() for code in selected_courses.split(',') if code.strip()]
    plan = service.create_plan_for_student(user.id, selected_course_codes)
    return RedirectResponse(url=request.url_for("user_home_view"), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/app/update-course-status")
async def update_course_status(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    course_code: str = Form(...),
    semester: str = Form(...),
    course_status: str = Form(...),
    grade: str = Form(default=""),
):
    repo = MyAdvisorRepository(db)
    service = MyAdvisorService(repo)

    if not course_code.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course code is required.")

    cleaned_grade = grade.strip() if grade and grade.strip() else None
    try:
        service.update_student_course_status(user.id, course_code.strip(), semester.strip(), course_status.strip(), cleaned_grade)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    redirect_url = f"{request.url_for('user_home_view')}#progress-page"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)