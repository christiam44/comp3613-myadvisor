from tests.conftest import PASSWORD


def _submit(client, headers, codes=("COMP 101", "MATH 220")):
    return client.post("/api/plans", json={"course_codes": list(codes)}, headers=headers)


def test_login_success(client, student):
    r = client.post("/api/login", json={"username": "student1", "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_login_wrong_password(client, student):
    r = client.post("/api/login", json={"username": "student1", "password": "nope"})
    assert r.status_code == 401


def test_courses_requires_login(client):
    assert client.get("/api/courses").status_code == 401


def test_course_search_filters(client, student_headers, seeded):
    r = client.get("/api/courses?q=comp", headers=student_headers)
    assert r.status_code == 200
    assert r.json() and all("comp" in c["course_code"].lower() or "comp" in c["title"].lower() for c in r.json())


def test_submit_plan_then_advisor_sees_it(client, student_headers, advisor_headers, seeded):
    r = _submit(client, student_headers)
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
    assert r.json()["total_credits"] == 6
    queue = client.get("/api/plans?status=pending", headers=advisor_headers)
    assert queue.status_code == 200
    assert len(queue.json()) == 1


def test_submit_empty_plan_rejected(client, student_headers, seeded):
    assert client.post("/api/plans", json={"course_codes": []}, headers=student_headers).status_code == 400


def test_submit_unknown_course_rejected(client, student_headers, seeded):
    assert _submit(client, student_headers, codes=("FAKE 999",)).status_code == 400


def test_student_cannot_view_advisor_queue(client, student_headers):
    assert client.get("/api/plans", headers=student_headers).status_code == 403


def test_advisor_cannot_submit_plan(client, advisor_headers, seeded):
    assert _submit(client, advisor_headers).status_code == 403


def test_review_requires_notes(client, student_headers, advisor_headers, seeded):
    plan_id = _submit(client, student_headers).json()["id"]
    r = client.put(f"/api/plans/{plan_id}/review", json={"decision": "approved", "notes": "  "}, headers=advisor_headers)
    assert r.status_code == 400


def test_review_unknown_plan_404(client, advisor_headers):
    r = client.put("/api/plans/999/review", json={"decision": "approved", "notes": "ok"}, headers=advisor_headers)
    assert r.status_code == 404


def test_request_changes_visible_to_student(client, student_headers, advisor_headers, seeded):
    plan_id = _submit(client, student_headers).json()["id"]
    r = client.put(f"/api/plans/{plan_id}/review",
                   json={"decision": "flagged_for_changes", "notes": "Swap MATH 220"}, headers=advisor_headers)
    assert r.status_code == 200
    mine = client.get("/api/plans/mine", headers=student_headers).json()
    assert mine["status"] == "flagged_for_changes"
    assert mine["advising_session_notes"] == "Swap MATH 220"


def test_approval_marks_courses_in_progress(client, student_headers, advisor_headers, seeded):
    plan_id = _submit(client, student_headers).json()["id"]
    client.put(f"/api/plans/{plan_id}/review", json={"decision": "approved", "notes": "Good"}, headers=advisor_headers)
    progress = client.get("/api/progress", headers=student_headers).json()
    assert progress["in_progress_count"] == 2
    assert progress["completed_credits"] == 0


def test_mark_complete_adds_credits(client, student_headers, advisor_headers, seeded):
    plan_id = _submit(client, student_headers).json()["id"]
    client.put(f"/api/plans/{plan_id}/review", json={"decision": "approved", "notes": "Good"}, headers=advisor_headers)
    r = client.put("/api/records/COMP 101", json={"status": "completed", "grade": "A"}, headers=student_headers)
    assert r.status_code == 200
    progress = client.get("/api/progress", headers=student_headers).json()
    assert progress["completed_credits"] == 3
    assert progress["completed_count"] == 1
    assert progress["in_progress_count"] == 1


def test_invalid_grade_rejected(client, student_headers, seeded):
    r = client.put("/api/records/COMP 101", json={"status": "completed", "grade": "Z"}, headers=student_headers)
    assert r.status_code == 400