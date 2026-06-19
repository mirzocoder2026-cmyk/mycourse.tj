import os
import uuid
from functools import wraps

from flask import Flask, request, jsonify, session, send_from_directory, render_template
from werkzeug.utils import secure_filename
import anthropic

from config import Config
from models import (
    db, User, Topic, Video, Test, Question, TestAttempt,
    Task, TaskSubmission, GroupMessage, AiMessage,
)

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)

db.init_app(app)

claude_client = None
if app.config.get("ANTHROPIC_API_KEY"):
    claude_client = anthropic.Anthropic(api_key=app.config["ANTHROPIC_API_KEY"])


# ─────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Шумо ворид нашудаед"}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Шумо ворид нашудаед"}), 401
        user = User.query.get(session["user_id"])
        if not user or user.role != "admin":
            return jsonify({"error": "Дастрасӣ манъ аст"}), 403
        return f(*args, **kwargs)
    return wrapper


def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None


def allowed_video(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in app.config["ALLOWED_VIDEO_EXT"]


# ─────────────────────────────────────────────────────────────────────────
# Page routes (serve frontend)
# ─────────────────────────────────────────────────────────────────────────
@app.route("/")
def page_index():
    return render_template("index.html")


@app.route("/login")
def page_login():
    return render_template("login.html")


@app.route("/admin")
def page_admin():
    return render_template("admin.html")


@app.route("/pupil")
def page_pupil():
    return render_template("pupil.html")


@app.route("/chat")
def page_chat():
    return render_template("chat.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ─────────────────────────────────────────────────────────────────────────
# Auth API
# ─────────────────────────────────────────────────────────────────────────
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Логин ё парол нодуруст аст"}), 401

    session["user_id"] = user.id
    return jsonify({"user": user.to_dict()})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def api_me():
    user = current_user()
    if not user:
        return jsonify({"user": None})
    return jsonify({"user": user.to_dict()})


# ─────────────────────────────────────────────────────────────────────────
# Users (admin manages pupils)
# ─────────────────────────────────────────────────────────────────────────
@app.route("/api/users", methods=["GET"])
@login_required
def api_users_list():
    users = User.query.filter_by(role="pupil").order_by(User.score.desc()).all()
    return jsonify([u.to_dict() for u in users])


@app.route("/api/users", methods=["POST"])
@admin_required
def api_users_create():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or len(password) < 4:
        return jsonify({"error": "Маълумоти нопурра"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Ин имейл аллакай мавҷуд аст"}), 400

    user = User(name=name, email=email, role="pupil")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@admin_required
def api_users_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        return jsonify({"error": "Админро ӯчиридан мумкин нест"}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────
# Rating
# ─────────────────────────────────────────────────────────────────────────
@app.route("/api/rating")
@login_required
def api_rating():
    users = User.query.filter_by(role="pupil").order_by(User.score.desc()).all()
    return jsonify([u.to_dict() for u in users])


# ─────────────────────────────────────────────────────────────────────────
# Topics
# ─────────────────────────────────────────────────────────────────────────
@app.route("/api/topics", methods=["GET"])
@login_required
def api_topics_list():
    topics = Topic.query.order_by(Topic.created_at).all()
    return jsonify([t.to_dict() for t in topics])


@app.route("/api/topics", methods=["POST"])
@admin_required
def api_topics_create():
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Унвон лозим аст"}), 400

    topic = Topic(
        title=title,
        description=data.get("description", ""),
        icon=data.get("icon", "📚"),
        color=data.get("color", "#2563EB"),
    )
    db.session.add(topic)
    db.session.commit()
    return jsonify(topic.to_dict()), 201


@app.route("/api/topics/<int:topic_id>", methods=["DELETE"])
@admin_required
def api_topics_delete(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    db.session.delete(topic)
    db.session.commit()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────
# Videos (real file upload to disk)
# ─────────────────────────────────────────────────────────────────────────
@app.route("/api/videos", methods=["GET"])
@login_required
def api_videos_list():
    videos = Video.query.order_by(Video.uploaded_at.desc()).all()
    return jsonify([v.to_dict() for v in videos])


@app.route("/api/videos", methods=["POST"])
@admin_required
def api_videos_create():
    title = (request.form.get("title") or "").strip()
    topic_id = request.form.get("topic_id") or None
    duration = request.form.get("duration", "0:00")
    file = request.files.get("video")

    if not title or not file or file.filename == "":
        return jsonify({"error": "Унвон ва файли видео лозим аст"}), 400
    if not allowed_video(file.filename):
        return jsonify({"error": "Формати видео дастгирӣ намешавад"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(stored_name)))

    video = Video(
        title=title,
        filename=stored_name,
        topic_id=int(topic_id) if topic_id else None,
        duration=duration,
    )
    db.session.add(video)
    db.session.commit()
    return jsonify(video.to_dict()), 201


@app.route("/api/videos/<int:video_id>", methods=["DELETE"])
@admin_required
def api_videos_delete(video_id):
    video = Video.query.get_or_404(video_id)
    try:
        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], video.filename))
    except OSError:
        pass
    db.session.delete(video)
    db.session.commit()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────
@app.route("/api/tests", methods=["GET"])
@login_required
def api_tests_list():
    tests = Test.query.order_by(Test.created_at.desc()).all()
    user = current_user()
    done_ids = set()
    if user.role == "pupil":
        done_ids = {a.test_id for a in TestAttempt.query.filter_by(user_id=user.id).all()}
    result = []
    for t in tests:
        d = t.to_dict(include_questions=(user.role == "admin"))
        d["completed"] = t.id in done_ids
        result.append(d)
    return jsonify(result)


@app.route("/api/tests/<int:test_id>", methods=["GET"])
@login_required
def api_test_detail(test_id):
    test = Test.query.get_or_404(test_id)
    return jsonify(test.to_dict(include_questions=True))


@app.route("/api/tests", methods=["POST"])
@admin_required
def api_tests_create():
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    topic_id = data.get("topic_id")
    questions = data.get("questions", [])

    if not title or not questions:
        return jsonify({"error": "Унвон ва ҳадди ақал 1 савол лозим аст"}), 400

    test = Test(title=title, topic_id=topic_id)
    db.session.add(test)
    db.session.flush()

    for q in questions:
        question = Question(
            test_id=test.id,
            text=q.get("q", ""),
            options=q.get("opts", []),
            correct_index=q.get("ans", 0),
        )
        db.session.add(question)

    db.session.commit()
    return jsonify(test.to_dict()), 201


@app.route("/api/tests/<int:test_id>", methods=["DELETE"])
@admin_required
def api_tests_delete(test_id):
    test = Test.query.get_or_404(test_id)
    db.session.delete(test)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/tests/<int:test_id>/submit", methods=["POST"])
@login_required
def api_tests_submit(test_id):
    user = current_user()
    test = Test.query.get_or_404(test_id)
    data = request.get_json(force=True)
    answers = data.get("answers", {})  # {question_index: selected_option_index}

    existing = TestAttempt.query.filter_by(test_id=test_id, user_id=user.id).first()
    if existing:
        return jsonify({"error": "Шумо аллакай ин тестро гузаштаед", "already_done": True}), 400

    questions = test.questions
    correct = 0
    for i, q in enumerate(questions):
        if str(i) in answers and int(answers[str(i)]) == q.correct_index:
            correct += 1

    total = len(questions)
    points = correct * 30

    attempt = TestAttempt(test_id=test_id, user_id=user.id, correct_count=correct, total=total, points_earned=points)
    db.session.add(attempt)
    user.score = (user.score or 0) + points
    db.session.commit()

    return jsonify({
        "correct": correct,
        "total": total,
        "points_earned": points,
        "percent": round(correct / total * 100) if total else 0,
        "new_score": user.score,
    })


# ─────────────────────────────────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────────────────────────────────
@app.route("/api/tasks", methods=["GET"])
@login_required
def api_tasks_list():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    user = current_user()
    solved_ids = set()
    if user.role == "pupil":
        solved_ids = {s.task_id for s in TaskSubmission.query.filter_by(user_id=user.id).all()}
    result = []
    for t in tasks:
        d = t.to_dict()
        d["solved"] = t.id in solved_ids
        result.append(d)
    return jsonify(result)


@app.route("/api/tasks", methods=["POST"])
@admin_required
def api_tasks_create():
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    text = (data.get("text") or "").strip()
    if not title or not text:
        return jsonify({"error": "Унвон ва матн лозим аст"}), 400

    task = Task(
        title=title,
        text=text,
        topic_id=data.get("topic_id"),
        difficulty=data.get("difficulty", "Осон"),
        points=int(data.get("points", 50)),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@admin_required
def api_tasks_delete(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/tasks/<int:task_id>/submit", methods=["POST"])
@login_required
def api_tasks_submit(task_id):
    user = current_user()
    task = Task.query.get_or_404(task_id)
    data = request.get_json(force=True)
    answer_text = (data.get("answer") or "").strip()

    if not answer_text:
        return jsonify({"error": "Ҷавоб холӣ аст"}), 400

    existing = TaskSubmission.query.filter_by(task_id=task_id, user_id=user.id).first()
    if existing:
        return jsonify({"error": "Шумо аллакай ҷавоб додаед", "already_done": True}), 400

    submission = TaskSubmission(task_id=task_id, user_id=user.id, answer_text=answer_text)
    db.session.add(submission)
    user.score = (user.score or 0) + task.points
    user.solved = (user.solved or 0) + 1
    db.session.commit()

    return jsonify({"points_earned": task.points, "new_score": user.score})


# ─────────────────────────────────────────────────────────────────────────
# Group chat
# ─────────────────────────────────────────────────────────────────────────
@app.route("/api/chat/group", methods=["GET"])
@login_required
def api_group_messages():
    msgs = GroupMessage.query.order_by(GroupMessage.created_at).limit(200).all()
    return jsonify([m.to_dict() for m in msgs])


@app.route("/api/chat/group", methods=["POST"])
@login_required
def api_group_send():
    user = current_user()
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Хабар холӣ аст"}), 400

    msg = GroupMessage(user_id=user.id, text=text)
    db.session.add(msg)
    db.session.commit()
    return jsonify(msg.to_dict()), 201


# ─────────────────────────────────────────────────────────────────────────
# AI chat (Flask -> Anthropic API, key stays server-side)
# ─────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Ту AI Ёрдамчии платформаи таълимии EduPlatform барои хонандагони тоҷик ҳастӣ. "
    "Ба забони тоҷикӣ ҷавоб деҳ. Дар мавзӯъҳои математика, физика, химия, алгебра, "
    "геометрия кӯмак кун. Ҷавобҳоят кӯтоҳ, возеҳ ва дастрас бошанд. Агар хонанда саволи "
    "математикӣ диҳад, мисолеро қадам ба қадам ҳал кун."
)


@app.route("/api/chat/ai/history", methods=["GET"])
@login_required
def api_ai_history():
    user = current_user()
    msgs = AiMessage.query.filter_by(user_id=user.id).order_by(AiMessage.created_at).all()
    return jsonify([{"role": m.role, "content": m.content} for m in msgs])


@app.route("/api/chat/ai", methods=["POST"])
@login_required
def api_ai_chat():
    if not claude_client:
        return jsonify({"error": "ANTHROPIC_API_KEY дар .env танзим нашудааст"}), 500

    user = current_user()
    data = request.get_json(force=True)
    user_text = (data.get("message") or "").strip()
    if not user_text:
        return jsonify({"error": "Хабар холӣ аст"}), 400

    # Save user message
    db.session.add(AiMessage(user_id=user.id, role="user", content=user_text))
    db.session.commit()

    # Build history for context (last 20 messages)
    history = AiMessage.query.filter_by(user_id=user.id).order_by(AiMessage.created_at).all()
    messages = [{"role": m.role, "content": m.content} for m in history[-20:]]

    try:
        response = claude_client.messages.create(
            model=app.config["CLAUDE_MODEL"],
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply_text = "".join(block.text for block in response.content if block.type == "text")
    except Exception as e:
        reply_text = "❌ Хато ҳангоми пайвастшавӣ ба AI. Боз ҳаракат кунед."
        app.logger.error(f"Anthropic API error: {e}")

    db.session.add(AiMessage(user_id=user.id, role="assistant", content=reply_text))
    db.session.commit()

    return jsonify({"reply": reply_text})


# ─────────────────────────────────────────────────────────────────────────
# DB seeding
# ─────────────────────────────────────────────────────────────────────────
def seed_database():
    if User.query.first():
        return  # already seeded

    admin = User(name="Алишер Каримов", email="admin@edu.tj", role="admin")
    admin.set_password("admin123")
    db.session.add(admin)

    pupils_data = [
        ("Баҳор Раҳимова", "bahora@edu.tj", 2450, 34),
        ("Сарвар Назаров", "sarvar@edu.tj", 2100, 28),
        ("Малика Юсупова", "malika@edu.tj", 1870, 24),
        ("Фирӯз Ҳасанов", "firuz@edu.tj", 1650, 19),
        ("Зарина Холова", "zarina@edu.tj", 1420, 16),
    ]
    for name, email, score, solved in pupils_data:
        p = User(name=name, email=email, role="pupil", score=score, solved=solved)
        p.set_password("123456")
        db.session.add(p)

    topics_data = [
        ("Алгебра — Асосҳо", "Амалиёт бо ифодаҳои алгебравӣ", "📐", "#2563EB"),
        ("Геометрия", "Шаклҳо, кунҷҳо ва теоремаҳо", "📏", "#7C3AED"),
        ("Физика — Механика", "Қонунҳои Нютон ва ҳаракат", "⚡", "#059669"),
        ("Химия — Асосҳо", "Элементҳо ва реаксияҳо", "🧪", "#D97706"),
    ]
    topics = []
    for title, desc, icon, color in topics_data:
        t = Topic(title=title, description=desc, icon=icon, color=color)
        db.session.add(t)
        topics.append(t)
    db.session.flush()

    tasks_data = [
        (topics[0].id, "Масъала №1", "Агар x + 3y = 12 ва 2x - y = 5 бошад, x ва y-ро ёбед.", "Осон", 50),
        (topics[1].id, "Масъала №2", "Квадрати тарафи 6 см ва 8 см доштаро ёбед. Диагоналашро ҳисоб кунед.", "Миёна", 100),
        (topics[2].id, "Масъала №3", "Ҷисме бо суръати 20 м/с ҳаракат мекунад. Агар суръатбандӣ 4 м/с² бошад, баъд аз 5 сония суръаташ чанд м/с мешавад?", "Осон", 50),
        (topics[3].id, "Масъала №4", "Оби 2H₂ + O₂ ташкил мекунад. Агар 4 г водород дошта бошем, чанд г об ҳосил мешавад?", "Душвор", 150),
    ]
    for topic_id, title, text, diff, pts in tasks_data:
        db.session.add(Task(topic_id=topic_id, title=title, text=text, difficulty=diff, points=pts))

    test1 = Test(topic_id=topics[0].id, title="Тест: Ифодаҳои алгебравӣ")
    db.session.add(test1)
    db.session.flush()
    for q, opts, ans in [
        ("2x + 5 = 11, x = ?", ["2", "3", "4", "5"], 1),
        ("x² - 9 = 0, x = ?", ["±2", "±3", "±4", "±9"], 1),
        ("3(x - 2) = 9, x = ?", ["3", "4", "5", "6"], 2),
    ]:
        db.session.add(Question(test_id=test1.id, text=q, options=opts, correct_index=ans))

    test2 = Test(topic_id=topics[2].id, title="Тест: Қонунҳои Нютон")
    db.session.add(test2)
    db.session.flush()
    for q, opts, ans in [
        ("F = ma — ин қонуни чандуми Нютон?", ["Аввал", "Дуюм", "Сеюм", "Чорум"], 1),
        ("Агар v = 0 ва a = 0 бошад, объект дар ҳолати чӣ қарор дорад?", ["Суръат", "Оромӣ", "Ҷаҳиш", "Давр"], 1),
    ]:
        db.session.add(Question(test_id=test2.id, text=q, options=opts, correct_index=ans))

    db.session.add(GroupMessage(user_id=admin.id, text="Салом ҳамаи хонандагон! Дарси имрӯза дар соати 14:00 оғоз мешавад."))

    db.session.commit()
    print("✅ Database seeded with demo data.")


@app.cli.command("seed")
def seed_command():
    """Run with: flask seed"""
    seed_database()


with app.app_context():
    db.create_all()
    seed_database()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
