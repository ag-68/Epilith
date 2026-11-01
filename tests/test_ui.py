from fastapi.testclient import TestClient

from ui.app import app


def test_home_page_is_the_lookup():
    page = TestClient(app).get("/")
    assert page.status_code == 200
    assert "Look up a company" in page.text or "Epilith" in page.text


def test_memo_list_includes_nvidia_when_present():
    rows = TestClient(app).get("/api/memos").json()
    assert isinstance(rows, list)
    nvidia = [row for row in rows if row["ticker"] == "NVDA"]
    if not nvidia:
        return
    assert nvidia[0]["conclusion"] in {"Candidate", "Watch", "Avoid"}
    memo = TestClient(app).get(f"/api/memos/{nvidia[0]['entry_id']}")
    assert memo.status_code == 200
    body = memo.json()
    assert "NVIDIA" in body["markdown"]
    assert body["conclusion"] == nvidia[0]["conclusion"]


def test_run_rejects_an_empty_query():
    response = TestClient(app).get("/api/run?q=")
    assert response.status_code == 400
