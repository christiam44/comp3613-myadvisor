from typing import Annotated
from fastapi import Depends, HTTPException, status, Request
import jwt
from jwt.exceptions import InvalidTokenError
from app.config import get_settings
from app.models.user import User
from app.dependencies.session import SessionDep
from app.repositories.user import UserRepository

async def get_current_user(request: Request, db: SessionDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Browser sessions use the cookie; API clients (Postman, pytest) can send
    # an "Authorization: Bearer <token>" header instead.
    token = request.cookies.get("access_token")
    if token is None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[get_settings().jwt_algorithm],
        )
        user_id = payload.get("sub", None)
    except InvalidTokenError as e:
        print("Invalid token error: ", e)
        raise credentials_exception

    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if user is None:
        raise credentials_exception
    return user

async def is_logged_in(request: Request, db: SessionDep):
    try:
        await get_current_user(request, db)
        return True
    except Exception:
        return False

IsUserLoggedIn = Annotated[bool, Depends(is_logged_in)]
AuthDep = Annotated[User, Depends(get_current_user)]

async def is_admin(user: User):
    return user.role in {"admin", "advisor"}

# Logged in but wrong role -> 403 (not 401, which means "not authenticated").
async def is_admin_dep(user: AuthDep):
    if not await is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this page",
        )
    return user

AdminDep = Annotated[User, Depends(is_admin_dep)]

# Students only: advisors/admins are rejected with 403.
async def is_student_dep(user: AuthDep):
    if await is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is for students only",
        )
    return user

StudentDep = Annotated[User, Depends(is_student_dep)]