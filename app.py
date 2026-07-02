import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from bson import ObjectId
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from werkzeug.security import check_password_hash, generate_password_hash


SEED_BOOKS = [
    {"title": "Introduction to Algorithms", "author": "Thomas H. Cormen", "isbn": "9780262046305", "category": "Computer Science", "shelf": "CS-A12", "total": 5, "available": 5},
    {"title": "Clean Code", "author": "Robert C. Martin", "isbn": "9780132350884", "category": "Software Engineering", "shelf": "SE-B04", "total": 4, "available": 3},
    {"title": "Database System Concepts", "author": "Abraham Silberschatz", "isbn": "9780078022159", "category": "Database", "shelf": "DB-C08", "total": 6, "available": 6},
    {"title": "Artificial Intelligence: A Modern Approach", "author": "Stuart Russell", "isbn": "9780134610993", "category": "Artificial Intelligence", "shelf": "AI-D03", "total": 3, "available": 2},
    {"title": "The Pragmatic Programmer", "author": "David Thomas", "isbn": "9780135957059", "category": "Software Engineering", "shelf": "SE-B09", "total": 5, "available": 5},
    {"title": "Computer Networks", "author": "Andrew S. Tanenbaum", "isbn": "9780132126953", "category": "Networking", "shelf": "NW-E06", "total": 4, "available": 4},
    {"title": "Operating System Concepts", "author": "Abraham Silberschatz", "isbn": "9781119800361", "category": "Operating Systems", "shelf": "OS-F02", "total": 5, "available": 4},
    {"title": "Python Crash Course", "author": "Eric Matthes", "isbn": "9781718502703", "category": "Programming", "shelf": "PR-G11", "total": 7, "available": 7},
]

memory = {"books": [], "transactions": []}


class Store:
    def __init__(self, app):
        self.db = None
        try:
            client = MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=600)
            client.admin.command("ping")
            self.db = client.get_default_database()
            if self.db.books.count_documents({}) == 0:
                self.db.books.insert_many(SEED_BOOKS)
        except (PyMongoError, TypeError):
            if not memory["books"]:
                memory["books"] = [dict(book, _id=str(index + 1)) for index, book in enumerate(SEED_BOOKS)]

    @property
    def mode(self):
        return "mongodb" if self.db is not None else "memory"

    def books(self):
        rows = list(self.db.books.find().sort("title", 1)) if self.db is not None else list(memory["books"])
        return [self.clean(row) for row in rows]

    def book(self, book_id):
        if self.db is not None:
            try:
                row = self.db.books.find_one({"_id": ObjectId(book_id)})
            except Exception:
                row = None
        else:
            row = next((book for book in memory["books"] if str(book["_id"]) == str(book_id)), None)
        return self.clean(row) if row else None

    def add_book(self, data):
        if self.db is not None:
            self.db.books.insert_one(data)
        else:
            data["_id"] = str(max([int(x["_id"]) for x in memory["books"]] or [0]) + 1)
            memory["books"].append(data)

    def delete_book(self, book_id):
        if self.db is not None:
            book = self.db.books.find_one({"_id": ObjectId(book_id)})
            if book and book["available"] == book["total"]:
                self.db.books.delete_one({"_id": book["_id"]})
        else:
            memory["books"] = [x for x in memory["books"] if not (str(x["_id"]) == book_id and x["available"] == x["total"])]

    def transactions(self):
        rows = list(self.db.transactions.find().sort("issued_at", -1)) if self.db is not None else list(reversed(memory["transactions"]))
        return [self.clean(row) for row in rows]

    def issue(self, book_id, student):
        book = self.book(book_id)
        if not book or book["available"] < 1:
            return False
        transaction = {
            "book_id": book_id, "book_title": book["title"], **student,
            "status": "issued", "issued_at": datetime.now(timezone.utc),
            "due_at": datetime.now(timezone.utc) + timedelta(days=14), "returned_at": None,
        }
        if self.db is not None:
            self.db.books.update_one({"_id": ObjectId(book_id), "available": {"$gt": 0}}, {"$inc": {"available": -1}})
            self.db.transactions.insert_one(transaction)
        else:
            next(x for x in memory["books"] if str(x["_id"]) == book_id)["available"] -= 1
            transaction["_id"] = str(len(memory["transactions"]) + 1)
            memory["transactions"].append(transaction)
        return True

    def return_book(self, transaction_id):
        if self.db is not None:
            tx = self.db.transactions.find_one({"_id": ObjectId(transaction_id), "status": "issued"})
            if not tx:
                return False
            self.db.transactions.update_one({"_id": tx["_id"]}, {"$set": {"status": "returned", "returned_at": datetime.now(timezone.utc)}})
            self.db.books.update_one({"_id": ObjectId(tx["book_id"])}, {"$inc": {"available": 1}})
        else:
            tx = next((x for x in memory["transactions"] if str(x["_id"]) == transaction_id and x["status"] == "issued"), None)
            if not tx:
                return False
            tx.update(status="returned", returned_at=datetime.now(timezone.utc))
            next(x for x in memory["books"] if str(x["_id"]) == tx["book_id"])["available"] += 1
        return True

    @staticmethod
    def clean(row):
        row = dict(row)
        row["_id"] = str(row["_id"])
        return row


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", secrets.token_hex(24)),
        MONGO_URI=os.getenv("MONGO_URI", "mongodb://localhost:27017/college_library"),
        ADMIN_USERNAME=os.getenv("ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD_HASH") or generate_password_hash("admin123"),
    )
    if config:
        app.config.update(config)

    def get_store():
        if "store" not in app.extensions:
            app.extensions["store"] = Store(app)
        return app.extensions["store"]

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("admin"):
                return redirect(url_for("admin_login"))
            return view(*args, **kwargs)
        return wrapped

    @app.get("/")
    def catalog():
        books = get_store().books()
        return render_template("catalog.html", books=books, categories=sorted({x["category"] for x in books}))

    @app.get("/api/books")
    def api_books():
        query = request.args.get("q", "").lower()
        books = [x for x in get_store().books() if query in f"{x['title']} {x['author']} {x['isbn']} {x['category']}".lower()]
        return jsonify(books)

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            valid_user = request.form.get("username") == app.config["ADMIN_USERNAME"]
            valid_password = check_password_hash(app.config["ADMIN_PASSWORD_HASH"], request.form.get("password", ""))
            if valid_user and valid_password:
                session["admin"] = True
                return redirect(url_for("admin_dashboard"))
            flash("Invalid username or password.", "error")
        return render_template("login.html")

    @app.get("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("catalog"))

    @app.get("/admin")
    @admin_required
    def admin_dashboard():
        store = get_store()
        books, transactions = store.books(), store.transactions()
        stats = {
            "titles": len(books), "copies": sum(x["total"] for x in books),
            "available": sum(x["available"] for x in books),
            "issued": sum(x["status"] == "issued" for x in transactions),
        }
        return render_template("admin.html", books=books, transactions=transactions[:6], stats=stats)

    @app.post("/admin/books")
    @admin_required
    def add_book():
        total = max(1, int(request.form.get("total", 1)))
        get_store().add_book({
            "title": request.form["title"].strip(), "author": request.form["author"].strip(),
            "isbn": request.form["isbn"].strip(), "category": request.form["category"].strip(),
            "shelf": request.form["shelf"].strip(), "total": total, "available": total,
        })
        flash("Book added successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/books/<book_id>/delete")
    @admin_required
    def delete_book(book_id):
        get_store().delete_book(book_id)
        flash("Book removed if no copy was issued.", "success")
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/issue")
    @admin_required
    def issue_book():
        ok = get_store().issue(request.form["book_id"], {
            "student_name": request.form["student_name"].strip(),
            "student_id": request.form["student_id"].strip(),
            "student_email": request.form["student_email"].strip(),
        })
        flash("Book issued for 14 days." if ok else "No copy is available.", "success" if ok else "error")
        return redirect(url_for("transactions"))

    @app.get("/admin/transactions")
    @admin_required
    def transactions():
        return render_template("transactions.html", transactions=get_store().transactions(), books=get_store().books())

    @app.post("/admin/transactions/<transaction_id>/return")
    @admin_required
    def return_book(transaction_id):
        get_store().return_book(transaction_id)
        flash("Book returned and inventory updated.", "success")
        return redirect(url_for("transactions"))

    @app.get("/api/health")
    def health():
        return jsonify(status="healthy", database=get_store().mode)

    return app


app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
