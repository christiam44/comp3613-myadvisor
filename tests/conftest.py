import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app import models  # noqa: F401  (registers all tables on the metadata)
from app.main import app as fastapi_app
from app.database import get_session
from app.models.user import User
from app.repositories.myadvisor import MyAdvisorRepository
from app.utilities.security import encrypt_password, create_access_token

PASSWORD = "testpass123"


@pytest.fixture
def engine():
    # In-memory SQLite, fresh for every test; never touches your real DB.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    def override_get_session():
        with Session(engine) as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = override_get_session
    # No "with" block on purpose: that would run the app lifespan against the real DB.
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


def make_user(db, username, role="regular_user"):
    user = User(
        username=username,
        email=f"{username}@test.com",
        password=encrypt_password(PASSWORD),
        role=role,
        first_name=username.capitalize(),
        last_name="Tester",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user):
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded(db):
    MyAdvisorRepository(db).ensure_program_and_courses()


@pytest.fixture
def student(db):
    return make_user(db, "student1")


@pytest.fixture
def advisor(db):
    return make_user(db, "advisor", role="advisor")


@pytest.fixture
def student_headers(student):
    return auth_headers(student)


@pytest.fixture
def advisor_headers(advisor):
    return auth_headers(advisor)