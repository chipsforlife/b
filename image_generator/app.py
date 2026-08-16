import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI, OpenAIError

load_dotenv()

app = Flask(__name__)

MODEL = "gpt-image-1"
ALLOWED_SIZES = {"1024x1024", "1024x1536", "1536x1024"}

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    if client is None:
        return jsonify(
            {"error": "Server is missing OPENAI_API_KEY. Set it in your .env file."}
        ), 500

    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    size = data.get("size", "1024x1024")

    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400
    if len(prompt) > 1000:
        return jsonify({"error": "Prompt is too long (max 1000 characters)."}), 400
    if size not in ALLOWED_SIZES:
        size = "1024x1024"

    try:
        result = client.images.generate(
            model=MODEL,
            prompt=prompt,
            size=size,
            n=1,
        )
    except OpenAIError as exc:
        # Surface API errors (bad key, billing, content policy) to the UI
        # instead of a generic 500 page.
        return jsonify({"error": str(exc)}), 502

    image_b64 = result.data[0].b64_json
    return jsonify({"image": f"data:image/png;base64,{image_b64}"})


if __name__ == "__main__":
    # Runs on a different port than the main app (app.py) so both can run together.
    app.run(debug=True, port=5001)
