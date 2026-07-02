import app as library


def make_client():
    library.memory["books"] = []
    library.memory["transactions"] = []
    app = library.create_app({"TESTING": True, "SECRET_KEY": "test", "MONGO_URI": ""})
    return app.test_client()


def login(client):
    return client.post("/admin/login", data={"username": "admin", "password": "admin123"})


def test_catalog_and_health():
    client = make_client()
    assert client.get("/").status_code == 200
    assert len(client.get("/api/books?q=python").json) == 1
    assert client.get("/api/health").json["status"] == "healthy"


def test_admin_requires_login():
    assert make_client().get("/admin").status_code == 302


def test_issue_and_return_flow():
    client = make_client()
    assert login(client).status_code == 302
    books = client.get("/api/books").json
    response = client.post("/admin/issue", data={"book_id": books[0]["_id"], "student_name": "Asha", "student_id": "CSE001", "student_email": "asha@example.com"})
    assert response.status_code == 302
    response = client.get("/admin/transactions")
    assert b"Asha" in response.data
    transaction_id = library.memory["transactions"][0]["_id"]
    client.post(f"/admin/transactions/{transaction_id}/return")
    assert library.memory["transactions"][0]["status"] == "returned"
