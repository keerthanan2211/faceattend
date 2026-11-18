from tests.conftest import ADMIN, PERSON_A, PERSON_A_2, PERSON_B, photo

TURN = {"left": 0.3, "right": -0.3}


def png(data: bytes, name: str):
    return (name, data, "image/png")


def scan(client, straight_rgb, turned_rgb=None, *, follow=True, straight_yaw=0.0, site="NH-44 Toll Plaza", token=None):
    """Runs the kiosk flow: get a challenge, then send a straight frame and a turned frame."""
    challenge = client.get("/api/attendance/challenge").json()
    direction = challenge["direction"]
    turn = TURN[direction] if follow else TURN["right" if direction == "left" else "left"]
    files = {
        "straight": png(photo(straight_rgb, straight_yaw), "a.png"),
        "turned": png(photo(turned_rgb or straight_rgb, turn), "b.png"),
    }
    return client.post(
        "/api/attendance/check-in", data={"site": site, "token": token or challenge["token"]}, files=files
    ), challenge


def test_admin_endpoints_need_the_key(client):
    assert client.get("/api/technicians").status_code == 401
    assert client.get("/api/technicians", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.get("/api/technicians", headers=ADMIN).status_code == 200


def test_challenge_picks_a_direction(client):
    c = client.get("/api/attendance/challenge").json()
    assert c["direction"] in {"left", "right"} and "." in c["token"]


def test_enrol_then_check_in_and_out(client, tech, monkeypatch):
    a = tech("NH-101", "Ravi Kumar", photo(PERSON_A), photo(PERSON_A_2))
    tech("NH-102", "Sita Devi", photo(PERSON_B))
    assert a["face_count"] == 2

    res, _ = scan(client, PERSON_A)
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "checked-in"
    assert res.json()["technician"]["employee_code"] == "NH-101"

    # An immediate second scan is confirmed (debounce), not turned into a check-out
    assert scan(client, PERSON_A)[0].json()["status"] == "already-recorded"

    monkeypatch.setenv("DEBOUNCE_SECONDS", "0")
    from app.config import get_settings

    get_settings.cache_clear()
    assert scan(client, PERSON_A)[0].json()["status"] == "checked-out"
    get_settings.cache_clear()
    assert [r["kind"] for r in client.get("/api/attendance", headers=ADMIN).json()] == ["out", "in"]


def test_photo_that_does_not_turn_fails_liveness(client, tech):
    tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    challenge = client.get("/api/attendance/challenge").json()
    still = {"straight": png(photo(PERSON_A), "a.png"), "turned": png(photo(PERSON_A), "b.png")}
    res = client.post("/api/attendance/check-in", data={"site": "Depot", "token": challenge["token"]}, files=still)
    assert res.status_code == 403
    assert "didn't see your head turn" in res.json()["detail"]
    assert client.get("/api/attendance/summary", headers=ADMIN).json()["unrecognised_today"] == 1


def test_turning_the_wrong_way_fails(client, tech):
    tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    res, _ = scan(client, PERSON_A, follow=False)
    assert res.status_code == 403 and "other way" in res.json()["detail"]


def test_not_looking_straight_first_fails(client, tech):
    tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    res, _ = scan(client, PERSON_A, straight_yaw=0.3)
    assert res.status_code == 403


def test_swapping_faces_between_frames_fails(client, tech):
    tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    tech("NH-102", "Sita Devi", photo(PERSON_B))
    res, _ = scan(client, PERSON_A, PERSON_B)
    assert res.status_code == 403 and "didn't match" in res.json()["detail"]


def test_challenge_cannot_be_replayed_or_forged(client, tech):
    tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    first, challenge = scan(client, PERSON_A)
    assert first.status_code == 200
    turn = TURN[challenge["direction"]]
    files = {"straight": png(photo(PERSON_A), "a.png"), "turned": png(photo(PERSON_A, turn), "b.png")}
    replay = client.post("/api/attendance/check-in", data={"site": "Depot", "token": challenge["token"]}, files=files)
    assert replay.status_code == 400 and "already submitted" in replay.json()["detail"]

    payload, sig = challenge["token"].split(".")
    forged = client.post(
        "/api/attendance/check-in", data={"site": "Depot", "token": f"{payload}.{sig[::-1]}"}, files=files
    )
    assert forged.status_code == 400


def test_unknown_face_is_rejected_and_logged(client, tech):
    tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    res, _ = scan(client, (30, 60, 220))
    assert res.status_code == 404 and "not recognised" in res.json()["detail"]
    assert client.get("/api/attendance/summary", headers=ADMIN).json()["unrecognised_today"] == 1


def test_inactive_technicians_cannot_check_in(client, tech):
    a = tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    client.patch(f"/api/technicians/{a['id']}", headers=ADMIN, json={"active": False})
    assert scan(client, PERSON_A)[0].status_code == 404


def test_templates_are_encrypted_at_rest(client, tech):
    from app.db import SessionLocal
    from app.models import FaceTemplate

    tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    with SessionLocal() as db:
        blob = db.query(FaceTemplate).one().ciphertext
    assert isinstance(blob, bytes) and len(blob) > 12
    assert b"0." not in blob  # not stored as readable numbers


def test_cannot_enrol_someone_elses_face(client, tech):
    tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    b = tech("NH-102", "Sita Devi")
    res = client.post(
        f"/api/technicians/{b['id']}/faces", headers=ADMIN, files=[("files", png(photo(PERSON_A_2), "x.png"))]
    )
    assert res.status_code == 409 and "Ravi Kumar" in res.json()["detail"]


def test_rejects_duplicate_photo_and_no_face(client, tech):
    a = tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    dup = client.post(
        f"/api/technicians/{a['id']}/faces", headers=ADMIN, files=[("files", png(photo(PERSON_A), "x.png"))]
    )
    assert dup.status_code == 409
    dark = client.post(
        f"/api/technicians/{a['id']}/faces", headers=ADMIN, files=[("files", png(photo((0, 0, 0)), "x.png"))]
    )
    assert dark.status_code == 422 and "No face" in dark.json()["detail"]


def test_rejects_non_images(client):
    token = client.get("/api/attendance/challenge").json()["token"]
    bad = {"straight": ("x.txt", b"hello", "text/plain"), "turned": ("y.txt", b"hello", "text/plain")}
    assert client.post("/api/attendance/check-in", data={"site": "Depot", "token": token}, files=bad).status_code == 422


def test_duplicate_employee_code(client, tech):
    tech("NH-101", "Ravi Kumar")
    body = {"employee_code": "nh-101", "name": "Other", "trade": "Surveyor", "phone": "9876543210"}
    assert client.post("/api/technicians", headers=ADMIN, json=body).status_code == 409


def test_summary_and_csv_export(client, tech):
    tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    scan(client, PERSON_A, site="Depot 3")
    summary = client.get("/api/attendance/summary", headers=ADMIN).json()
    assert summary["present_today"] == 1 and summary["on_site_now"] == ["Ravi Kumar"]
    lines = client.get("/api/attendance/export.csv", headers=ADMIN).text.strip().splitlines()
    assert lines[0].startswith("Date,Time (UTC),Employee code")
    assert "NH-101,Ravi Kumar,Check-in,Depot 3" in lines[1]


def test_deleting_a_technician_removes_their_faces(client, tech):
    a = tech("NH-101", "Ravi Kumar", photo(PERSON_A))
    assert client.delete(f"/api/technicians/{a['id']}", headers=ADMIN).status_code == 204
    assert scan(client, PERSON_A)[0].status_code == 404
