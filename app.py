import os

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from flask import Flask, redirect, render_template, request, url_for

load_dotenv()

app = Flask(__name__)

COLLECTION_NAME = "inspirations"


def init_firestore():
    """Initialize the Firebase Admin SDK from a service account JSON
    provided via environment variable, then return a Firestore client."""
    if not firebase_admin._apps:
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not cred_path or not os.path.exists(cred_path):
            raise RuntimeError(
                "Firebase credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                "in your .env file to the path of your service account JSON file."
            )
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


db = init_firestore()


@app.route("/")
def index():
    docs = db.collection(COLLECTION_NAME).stream()
    items = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        items.append(data)
    items.sort(key=lambda x: x.get("favorite", False), reverse=True)
    return render_template("index.html", items=items)


@app.route("/add", methods=["POST"])
def add_item():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "Visual Art")
    if title:
        db.collection(COLLECTION_NAME).add(
            {"title": title, "category": category, "favorite": False}
        )
    return redirect(url_for("index"))


@app.route("/favorite/<item_id>", methods=["POST"])
def favorite_item(item_id):
    doc_ref = db.collection(COLLECTION_NAME).document(item_id)
    doc = doc_ref.get()
    if doc.exists:
        current = doc.to_dict().get("favorite", False)
        doc_ref.update({"favorite": not current})
    return redirect(url_for("index"))


@app.route("/delete/<item_id>", methods=["POST"])
def delete_item(item_id):
    db.collection(COLLECTION_NAME).document(item_id).delete()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
