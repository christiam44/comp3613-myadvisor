from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request, status, Form
from app.dependencies import SessionDep
from app.dependencies.auth import get_current_user, is_admin
from . import router, templates
from app.services.auth_service import AuthService
from app.repositories.user import UserRepository
from app.utilities.flash import flash
from app.utilities.security import access_token_cookie_kwargs


@router.get("/login", response_class=HTMLResponse)
async def login_view(request: Request, db: SessionDep):
    token = request.cookies.get("access_token")
    if token:
        try:
            user = await get_current_user(request, db)
            dest = "admin_home_view" if await is_admin(user) else "user_home_view"
            return RedirectResponse(
                url=request.url_for(dest),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        except Exception:
            response = templates.TemplateResponse(
                request=request,
                name="login.html",
            )
            response.delete_cookie(key="access_token", **access_token_cookie_kwargs())
            return response

    return templates.TemplateResponse(
        request=request,
        name="login.html",
    )


@router.post("/login", response_class=HTMLResponse)
async def login_action_ajax(
    db: SessionDep,
    request: Request,
    username: str = Form(),
    password: str = Form(),
):
    request.cookies.get("access_token")
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    access_token = auth_service.authenticate_user(username, password)
    if not access_token:
        response = RedirectResponse(
            url=request.url_for("login_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.delete_cookie(key="access_token", **access_token_cookie_kwargs())
        flash(request, "Incorrect username or password", "danger")
        return response

    user = user_repo.get_by_username(username)
    dest = "admin_home_view" if user and user.role in {"admin", "advisor"} else "user_home_view"
    response = RedirectResponse(
        url=request.url_for(dest),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        **access_token_cookie_kwargs(),
    )
    return response
