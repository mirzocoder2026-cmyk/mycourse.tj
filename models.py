from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="pupil")  # 'admin' or 'pupil'
    score = db.Column(db.Integer, default=0)
    solved = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "score": self.score,
            "solved": self.solved,
        }


class Topic(db.Model):
    __tablename__ = "topics"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    icon = db.Column(db.String(10), default="📚")
    color = db.Column(db.String(10), default="#2563EB")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    videos = db.relationship("Video", backref="topic", lazy=True, cascade="all, delete-orphan")
    tests = db.relationship("Test", backref="topic", lazy=True, cascade="all, delete-orphan")
    tasks = db.relationship("Task", backref="topic", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
        }


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # stored filename on disk
    duration = db.Column(db.String(20), default="0:00")
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "topic_id": self.topic_id,
            "title": self.title,
            "url": f"/uploads/{self.filename}",
            "duration": self.duration,
            "uploaded_at": self.uploaded_at.strftime("%Y-%m-%d"),
        }


class Test(db.Model):
    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship("Question", backref="test", lazy=True, cascade="all, delete-orphan")
    attempts = db.relationship("TestAttempt", backref="test", lazy=True, cascade="all, delete-orphan")

    def to_dict(self, include_questions=True):
        d = {"id": self.id, "topic_id": self.topic_id, "title": self.title}
        if include_questions:
            d["questions"] = [q.to_dict() for q in self.questions]
        return d


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)  # list of strings
    correct_index = db.Column(db.Integer, nullable=False)

    def to_dict(self, reveal_answer=False):
        d = {"id": self.id, "text": self.text, "options": self.options}
        if reveal_answer:
            d["correct_index"] = self.correct_index
        return d


class TestAttempt(db.Model):
    __tablename__ = "test_attempts"

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("tests.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    correct_count = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    points_earned = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("test_id", "user_id", name="uniq_test_user"),)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default="Осон")  # Осон, Миёна, Душвор
    points = db.Column(db.Integer, default=50)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship("TaskSubmission", backref="task", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "topic_id": self.topic_id,
            "title": self.title,
            "text": self.text,
            "difficulty": self.difficulty,
            "points": self.points,
        }


class TaskSubmission(db.Model):
    __tablename__ = "task_submissions"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    answer_text = db.Column(db.Text, default="")
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("task_id", "user_id", name="uniq_task_user"),)


class GroupMessage(db.Model):
    __tablename__ = "group_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.user.name,
            "role": self.user.role,
            "text": self.text,
            "time": self.created_at.strftime("%H:%M"),
        }


class AiMessage(db.Model):
    """Per-user AI chat history so each pupil has their own conversation."""
    __tablename__ = "ai_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
