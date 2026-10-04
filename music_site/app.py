import base64
import io
import json
import math
import mimetypes
import os
import struct
import uuid
import wave
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import firebase_admin
import requests
from dotenv import load_dotenv
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials, firestore
from flask import Flask, abort, jsonify, render_template, request
from openai import OpenAI, OpenAIError

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

POSTS_COLLECTION = "posts"
COMMENTS_SUBCOLLECTION = "comments"

GENERATED_DIR = os.path.join(app.static_folder, "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)
mimetypes.add_type("application/vnd.recordare.musicxml+xml", ".musicxml")

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "").strip()
HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "stabilityai/stable-audio-open-1.0").strip()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

MIN_DURATION = 5
MAX_DURATION = 47
DEFAULT_DURATION = 20

GENRE_PRESETS = ["Lo-fi", "Ambient", "Piano", "Orchestral", "Synthwave", "Cinematic"]

# Mood options for the orchestra score generator - shown as a dropdown on
# the new-post page. Each also drives the local placeholder score (scale +
# tempo + dynamic) when OPENAI_API_KEY isn't configured yet.
MOOD_PRESETS = [
    {"value": "Happy", "label": "밝고 경쾌하게"},
    {"value": "Sad", "label": "슬프고 잔잔하게"},
    {"value": "Epic", "label": "웅장하고 영웅적으로"},
    {"value": "Mysterious", "label": "신비롭게"},
    {"value": "Peaceful", "label": "평화롭게"},
    {"value": "Tense", "label": "긴장감 있게"},
    {"value": "Triumphant", "label": "승리에 찬 팡파르처럼"},
    {"value": "Melancholic", "label": "애수 어린"},
    {"value": "Playful", "label": "장난스럽게"},
    {"value": "Dark", "label": "어둡고 무겁게"},
]
MOOD_VALUES = {m["value"] for m in MOOD_PRESETS}
MOOD_LABELS = {m["value"]: m["label"] for m in MOOD_PRESETS}

TEMPO_PRESETS = [
    {"value": "Slow", "label": "느리게", "bpm": 66},
    {"value": "Moderate", "label": "보통", "bpm": 100},
    {"value": "Fast", "label": "빠르게", "bpm": 138},
]
TEMPO_BPM = {t["value"]: t["bpm"] for t in TEMPO_PRESETS}
TEMPO_LABELS = {t["value"]: t["label"] for t in TEMPO_PRESETS}
DEFAULT_TEMPO = "Moderate"

# Root pitch (step, alter) + whole/half-step pattern per mood, used only by
# the offline placeholder score below.
MOOD_SCALES = {
    "Happy": ("C", 0, [0, 2, 4, 5, 7, 9, 11]),       # C major
    "Sad": ("A", 0, [0, 2, 3, 5, 7, 8, 10]),          # A minor
    "Epic": ("D", 0, [0, 2, 3, 5, 7, 8, 10]),         # D minor
    "Mysterious": ("D", 0, [0, 1, 4, 5, 7, 8, 10]),   # D phrygian-ish
    "Peaceful": ("F", 0, [0, 2, 4, 5, 7, 9, 11]),     # F major
    "Tense": ("B", 0, [0, 2, 3, 5, 7, 8, 10]),        # B minor
    "Triumphant": ("E", -1, [0, 2, 4, 5, 7, 9, 11]),  # Eb major
    "Melancholic": ("E", 0, [0, 2, 3, 5, 7, 8, 10]),  # E minor
    "Playful": ("G", 0, [0, 2, 4, 5, 7, 9, 11]),      # G major
    "Dark": ("C", 0, [0, 2, 3, 5, 7, 8, 10]),         # C minor
}


# ---------------------------------------------------------------------------
# Firebase / Firestore setup
#
# When a real service account isn't configured yet (e.g. before the Firebase
# project has been created), the app falls back to DEMO_MODE: an in-memory
# data store stands in for Firestore, and the auth layer accepts the local
# "demo." tokens issued by static/js/firebase-init.js's client-side emulator
# instead of verifying real Firebase ID tokens. This lets the whole site
# (login -> create post -> generate -> play -> comment) be exercised with
# zero external setup. As soon as GOOGLE_APPLICATION_CREDENTIALS points to a
# real service account, the app switches to real Firestore + real Firebase
# Auth automatically and demo tokens are no longer accepted.
# ---------------------------------------------------------------------------


def init_firestore():
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not os.path.exists(cred_path):
        return None
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


db = init_firestore()
DEMO_MODE = db is None

if DEMO_MODE:
    print(
        "[MoodTune] GOOGLE_APPLICATION_CREDENTIALS not set/found -> running in DEMO MODE "
        "(in-memory data, unverified local login). See README.md to connect a real "
        "Firebase project."
    )


class MemoryStore:
    """Minimal in-memory stand-in for the Firestore collections this app
    uses, so the site is fully clickable without a Firebase project."""

    def __init__(self):
        self.posts = {}  # post_id -> dict
        self.comments = {}  # post_id -> list[dict]

    def list_posts(self):
        return sorted(self.posts.values(), key=lambda p: p["created_at"], reverse=True)

    def get_post(self, post_id):
        return self.posts.get(post_id)

    def create_post(self, fields):
        post_id = uuid.uuid4().hex
        self.posts[post_id] = {"id": post_id, **fields}
        self.comments[post_id] = []
        return post_id

    def list_comments(self, post_id):
        return sorted(self.comments.get(post_id, []), key=lambda c: c["created_at"])

    def add_comment(self, post_id, fields):
        comment_id = uuid.uuid4().hex
        comment = {"id": comment_id, **fields}
        self.comments.setdefault(post_id, []).append(comment)
        self.posts[post_id]["comment_count"] = self.posts[post_id].get("comment_count", 0) + 1
        return comment_id


memory_store = MemoryStore() if DEMO_MODE else None


def list_posts():
    if DEMO_MODE:
        return memory_store.list_posts()
    docs = db.collection(POSTS_COLLECTION).order_by(
        "created_at", direction=firestore.Query.DESCENDING
    ).stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def get_post(post_id):
    if DEMO_MODE:
        return memory_store.get_post(post_id)
    doc = db.collection(POSTS_COLLECTION).document(post_id).get()
    return {"id": doc.id, **doc.to_dict()} if doc.exists else None


def create_post(fields):
    if DEMO_MODE:
        return memory_store.create_post(fields)
    _, doc_ref = db.collection(POSTS_COLLECTION).add(fields)
    return doc_ref.id


def list_comments(post_id):
    if DEMO_MODE:
        return memory_store.list_comments(post_id)
    post_ref = db.collection(POSTS_COLLECTION).document(post_id)
    docs = post_ref.collection(COMMENTS_SUBCOLLECTION).order_by("created_at").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def add_comment(post_id, fields):
    if DEMO_MODE:
        return memory_store.add_comment(post_id, fields)
    post_ref = db.collection(POSTS_COLLECTION).document(post_id)
    _, comment_ref = post_ref.collection(COMMENTS_SUBCOLLECTION).add(fields)
    post_ref.update({"comment_count": firestore.Increment(1)})
    return comment_ref.id


def get_current_user():
    """Identify the caller from the Authorization header.

    In real mode this verifies a Firebase ID token with firebase-admin. In
    DEMO_MODE (no Firebase project configured yet) it instead reads the
    unverified local "demo.<base64 json>" token issued by the client-side
    auth emulator in firebase-init.js - fine for local exploration, never
    for a real deployment.
    """
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    if not token:
        return None

    if DEMO_MODE:
        if not token.startswith("demo."):
            return None
        try:
            payload = json.loads(base64.urlsafe_b64decode(token[len("demo."):] + "==="))
        except Exception:
            return None
        return {
            "uid": payload.get("uid", "demo"),
            "email": payload.get("email", ""),
            "name": payload.get("displayName") or payload.get("email", "익명"),
        }

    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception:
        return None
    return {
        "uid": decoded.get("uid"),
        "email": decoded.get("email", ""),
        "name": decoded.get("name") or decoded.get("email", "익명"),
    }


def jsonify_error(status_code, message):
    response = jsonify({"error": message})
    response.status_code = status_code
    return response


def serialize_post(data):
    created_at = data.get("created_at")
    return {
        "id": data["id"],
        "title": data.get("title", ""),
        "prompt": data.get("prompt", ""),
        "genre": data.get("genre"),
        "duration": data.get("duration"),
        "audio_url": data.get("audio_url"),
        "is_demo_audio": data.get("is_demo_audio", False),
        "mood": data.get("mood"),
        "tempo": data.get("tempo"),
        "score_url": data.get("score_url"),
        "is_demo_score": data.get("is_demo_score", False),
        "author_name": data.get("author_name", "익명"),
        "author_uid": data.get("author_uid"),
        "comment_count": data.get("comment_count", 0),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else None,
    }


def serialize_comment(data):
    created_at = data.get("created_at")
    return {
        "id": data["id"],
        "text": data.get("text", ""),
        "author_name": data.get("author_name", "익명"),
        "author_uid": data.get("author_uid"),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else None,
    }


# ---------------------------------------------------------------------------
# Music generation
# ---------------------------------------------------------------------------

# Rough chord per genre preset, used only by the local placeholder synth
# below - purely cosmetic so different genre picks sound different from
# each other while the real Stable Audio integration isn't wired up yet.
GENRE_CHORDS = {
    "Lo-fi": [220.00, 261.63, 329.63],
    "Ambient": [196.00, 246.94, 293.66],
    "Piano": [261.63, 329.63, 392.00],
    "Orchestral": [174.61, 220.00, 261.63],
    "Synthwave": [233.08, 293.66, 349.23],
    "Cinematic": [146.83, 185.00, 220.00],
}
DEFAULT_CHORD = [220.00, 277.18, 329.63]


def synthesize_placeholder_audio(genre, duration):
    """Generate a short, gentle arpeggio locally (pure stdlib, no network).

    Used as a stand-in while HF_API_TOKEN isn't configured yet, so the full
    create-post -> play flow can be tried end to end today. Clearly flagged
    to the user as demo audio via the `is_demo_audio` post field.
    """
    sample_rate = 22050
    note_seconds = 0.6
    freqs = GENRE_CHORDS.get(genre, DEFAULT_CHORD)
    n_samples = int(sample_rate * duration)

    frames = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        note_index = int(t / note_seconds) % len(freqs)
        freq = freqs[note_index]
        phase = (t % note_seconds) / note_seconds
        envelope = 0.5 * (1 - math.cos(2 * math.pi * phase))  # smooth per-note swell
        sample = math.sin(2 * math.pi * freq * t) * envelope * 0.3
        value = int(max(-1.0, min(1.0, sample)) * 32767)
        frames += struct.pack("<h", value)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    return buffer.getvalue(), "audio/wav", True


def generate_audio(prompt, genre, duration):
    """Return (audio_bytes, content_type, is_demo_audio).

    Calls Hugging Face Inference Providers (Stable Audio) when HF_API_TOKEN
    is configured; otherwise falls back to a local placeholder tone so the
    site remains fully usable before the API key is issued. Raises
    RuntimeError with a user-facing message if the real call fails.
    """
    if not HF_API_TOKEN:
        return synthesize_placeholder_audio(genre, duration)

    full_prompt = f"{genre} style, {prompt}" if genre else prompt
    endpoint = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": full_prompt,
        "parameters": {"seconds_total": duration},
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=180)
    except requests.RequestException as exc:
        raise RuntimeError(f"음악 생성 서버 호출에 실패했습니다: {exc}") from exc

    content_type = response.headers.get("Content-Type", "")
    if response.status_code != 200 or not content_type.startswith("audio"):
        message = None
        try:
            error_json = response.json()
            message = error_json.get("error") or error_json.get("message")
        except ValueError:
            pass
        raise RuntimeError(message or f"음악 생성에 실패했습니다 (status {response.status_code}).")

    return response.content, content_type or "audio/wav", False


# ---------------------------------------------------------------------------
# Orchestral score (MusicXML) generation via ChatGPT
# ---------------------------------------------------------------------------

CHROMATIC_STEPS = [
    ("C", 0), ("C", 1), ("D", 0), ("D", 1), ("E", 0), ("F", 0),
    ("F", 1), ("G", 0), ("G", 1), ("A", 0), ("A", 1), ("B", 0),
]
STEP_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _scale_pitches(root_step, root_alter, intervals, octave, span):
    root_class = (STEP_SEMITONE[root_step] + root_alter) % 12
    pitches = []
    for i in range(span):
        offset = intervals[i % len(intervals)]
        octave_shift = i // len(intervals)
        step, alter = CHROMATIC_STEPS[(root_class + offset) % 12]
        pitches.append((step, alter, octave + octave_shift))
    return pitches


def build_placeholder_musicxml(mood, tempo_label, title):
    """A short, guaranteed-valid single-line melody (pure stdlib, no
    network) standing in for a real orchestral score while OPENAI_API_KEY
    isn't configured yet - so the whole create-post flow, score included,
    can be tried end to end today."""
    root_step, root_alter, intervals = MOOD_SCALES.get(mood, MOOD_SCALES["Happy"])
    bpm = TEMPO_BPM.get(tempo_label, TEMPO_BPM[DEFAULT_TEMPO])
    measures, notes_per_measure = 8, 4
    pitches = _scale_pitches(root_step, root_alter, intervals, octave=4, span=measures * notes_per_measure)

    score = ET.Element("score-partwise", version="3.1")
    work = ET.SubElement(score, "work")
    ET.SubElement(work, "work-title").text = title
    identification = ET.SubElement(score, "identification")
    ET.SubElement(identification, "creator", type="composer").text = "MoodTune (placeholder)"

    part_list = ET.SubElement(score, "part-list")
    score_part = ET.SubElement(part_list, "score-part", id="P1")
    ET.SubElement(score_part, "part-name").text = "Strings"

    part = ET.SubElement(score, "part", id="P1")
    idx = 0
    for m in range(1, measures + 1):
        measure = ET.SubElement(part, "measure", number=str(m))
        if m == 1:
            attributes = ET.SubElement(measure, "attributes")
            ET.SubElement(attributes, "divisions").text = "1"
            ET.SubElement(ET.SubElement(attributes, "key"), "fifths").text = "0"
            time = ET.SubElement(attributes, "time")
            ET.SubElement(time, "beats").text = "4"
            ET.SubElement(time, "beat-type").text = "4"
            clef = ET.SubElement(attributes, "clef")
            ET.SubElement(clef, "sign").text = "G"
            ET.SubElement(clef, "line").text = "2"

            direction = ET.SubElement(measure, "direction", placement="above")
            metronome = ET.SubElement(ET.SubElement(direction, "direction-type"), "metronome")
            ET.SubElement(metronome, "beat-unit").text = "quarter"
            ET.SubElement(metronome, "per-minute").text = str(bpm)
            ET.SubElement(direction, "sound", tempo=str(bpm))

        for _ in range(notes_per_measure):
            step, alter, octave = pitches[idx]
            idx += 1
            note = ET.SubElement(measure, "note")
            pitch = ET.SubElement(note, "pitch")
            ET.SubElement(pitch, "step").text = step
            if alter:
                ET.SubElement(pitch, "alter").text = str(alter)
            ET.SubElement(pitch, "octave").text = str(octave)
            ET.SubElement(note, "duration").text = "1"
            ET.SubElement(note, "type").text = "quarter"

    xml_body = ET.tostring(score, encoding="unicode")
    doctype = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" '
        '"http://www.musicxml.org/dtds/partwise.dtd">\n'
    )
    return doctype + xml_body


def _strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def generate_musicxml(prompt, mood, tempo_label, genre, title):
    """Return (musicxml_str, is_demo).

    Asks ChatGPT to compose a short orchestral excerpt matching the
    prompt/mood/tempo and return it as MusicXML. Falls back to a local
    placeholder melody when OPENAI_API_KEY isn't configured, so the score
    part of the flow works before the key is issued too. Raises
    RuntimeError with a user-facing message on failure.
    """
    if openai_client is None:
        return build_placeholder_musicxml(mood, tempo_label, title), True

    bpm = TEMPO_BPM.get(tempo_label, TEMPO_BPM[DEFAULT_TEMPO])
    system_prompt = (
        "You are an expert orchestral composer and MusicXML engineer. Given a short "
        "description, mood, tempo and genre, compose a short orchestral excerpt "
        "(8-16 measures, 3-5 parts such as strings, woodwinds, brass or timpani as "
        "fits the mood) and output it as a single, complete, well-formed MusicXML 3.1 "
        "<score-partwise> document. Respond with ONLY the raw XML - no markdown code "
        "fences, no commentary before or after."
    )
    user_prompt = (
        f"Description: {prompt}\n"
        f"Mood: {mood}\n"
        f"Tempo: {tempo_label} (~{bpm} BPM)\n"
        f"Genre: {genre or 'Orchestral'}\n"
        f"Title: {title}"
    )

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
        )
    except OpenAIError as exc:
        raise RuntimeError(f"악보 생성(ChatGPT) 호출에 실패했습니다: {exc}") from exc

    xml_text = _strip_code_fence(response.choices[0].message.content or "")
    if not xml_text:
        raise RuntimeError("ChatGPT가 빈 응답을 반환했습니다.")

    try:
        ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError as exc:
        raise RuntimeError(f"ChatGPT가 생성한 악보(MusicXML)가 올바르지 않습니다: {exc}") from exc

    return xml_text, False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.context_processor
def inject_labels():
    return {"mood_labels": MOOD_LABELS, "tempo_labels": TEMPO_LABELS}


@app.route("/")
def index():
    query = request.args.get("q", "").strip().lower()
    posts = [serialize_post(p) for p in list_posts()]

    if query:
        def matches(post):
            haystack = " ".join(
                filter(None, [post["title"], post["prompt"], post.get("genre") or ""])
            ).lower()
            return query in haystack

        posts = [p for p in posts if matches(p)]

    return render_template("index.html", posts=posts, query=query, demo_mode=DEMO_MODE)


@app.route("/login")
def login_page():
    return render_template("login.html", demo_mode=DEMO_MODE)


@app.route("/new")
def new_post_page():
    return render_template(
        "new_post.html",
        genres=GENRE_PRESETS,
        moods=MOOD_PRESETS,
        tempos=TEMPO_PRESETS,
        default_tempo=DEFAULT_TEMPO,
        default_duration=DEFAULT_DURATION,
        min_duration=MIN_DURATION,
        max_duration=MAX_DURATION,
        demo_mode=DEMO_MODE,
        hf_configured=bool(HF_API_TOKEN),
        openai_configured=bool(openai_client),
    )


@app.route("/post/<post_id>")
def post_detail(post_id):
    post = get_post(post_id)
    if not post:
        abort(404)
    comments = [serialize_comment(c) for c in list_comments(post_id)]
    return render_template(
        "post_detail.html", post=serialize_post(post), comments=comments, demo_mode=DEMO_MODE
    )


@app.route("/api/posts", methods=["POST"])
def create_post_route():
    user = get_current_user()
    if not user:
        return jsonify_error(401, "로그인이 필요합니다.")

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    prompt = (data.get("prompt") or "").strip()
    genre = (data.get("genre") or "").strip() or None
    mood = (data.get("mood") or "").strip()
    tempo = (data.get("tempo") or DEFAULT_TEMPO).strip()
    try:
        duration = int(data.get("duration", DEFAULT_DURATION))
    except (TypeError, ValueError):
        duration = DEFAULT_DURATION
    duration = max(MIN_DURATION, min(MAX_DURATION, duration))

    if not title:
        return jsonify_error(400, "제목을 입력해주세요.")
    if len(title) > 100:
        return jsonify_error(400, "제목은 100자 이내로 입력해주세요.")
    if not prompt:
        return jsonify_error(400, "프롬프트를 입력해주세요.")
    if len(prompt) > 500:
        return jsonify_error(400, "프롬프트는 500자 이내로 입력해주세요.")
    if mood not in MOOD_VALUES:
        return jsonify_error(400, "무드를 선택해주세요.")
    if tempo not in TEMPO_BPM:
        tempo = DEFAULT_TEMPO

    try:
        audio_bytes, content_type, is_demo_audio = generate_audio(prompt, genre, duration)
    except RuntimeError as exc:
        return jsonify_error(502, str(exc))

    ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".wav"
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(GENERATED_DIR, filename), "wb") as f:
        f.write(audio_bytes)
    audio_url = f"/static/generated/{filename}"

    try:
        score_xml, is_demo_score = generate_musicxml(prompt, mood, tempo, genre, title)
    except RuntimeError as exc:
        return jsonify_error(502, str(exc))

    score_filename = f"{uuid.uuid4().hex}.musicxml"
    with open(os.path.join(GENERATED_DIR, score_filename), "w", encoding="utf-8") as f:
        f.write(score_xml)
    score_url = f"/static/generated/{score_filename}"

    post_id = create_post({
        "title": title,
        "prompt": prompt,
        "genre": genre,
        "duration": duration,
        "audio_url": audio_url,
        "is_demo_audio": is_demo_audio,
        "mood": mood,
        "tempo": tempo,
        "score_url": score_url,
        "is_demo_score": is_demo_score,
        "author_uid": user["uid"],
        "author_name": user["name"],
        "created_at": datetime.now(timezone.utc),
        "comment_count": 0,
    })

    return jsonify(serialize_post(get_post(post_id))), 201


@app.route("/api/posts/<post_id>/comments", methods=["POST"])
def add_comment_route(post_id):
    user = get_current_user()
    if not user:
        return jsonify_error(401, "로그인이 필요합니다.")

    if not get_post(post_id):
        return jsonify_error(404, "게시글을 찾을 수 없습니다.")

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify_error(400, "댓글 내용을 입력해주세요.")
    if len(text) > 300:
        return jsonify_error(400, "댓글은 300자 이내로 입력해주세요.")

    comment_id = add_comment(post_id, {
        "text": text,
        "author_uid": user["uid"],
        "author_name": user["name"],
        "created_at": datetime.now(timezone.utc),
    })

    comment = next(c for c in list_comments(post_id) if c["id"] == comment_id)
    return jsonify(serialize_comment(comment)), 201


if __name__ == "__main__":
    # Runs on a different port so it can run alongside the other demo apps
    # in this repo (app.py on 5000, image_generator on 5001).
    app.run(debug=True, port=5002)
