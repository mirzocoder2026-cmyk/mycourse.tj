# EduPlatform — Backend (Flask + SQLAlchemy)

Платформаи таълимӣ бо backend воқеӣ: маълумот дар SQLite захира мешавад, видео дар диск нигоҳ дошта мешавад, ва AI чат тавассути сервер ба Anthropic API занг мезанад (калид ҳаргиз ба браузер намефиристад).

## 1. Насб кардан

```bash
cd eduplatform
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Танзими .env

Файли `.env.example`-ро нусха бардоред ва бо номи `.env` захира кунед:

```bash
cp .env.example .env
```

Дар `.env` инҳоро гузоред:

```
SECRET_KEY=як-рамзи-тасодуфии-дарозу-махфӣ
ANTHROPIC_API_KEY=sk-ant-...   ← калиди воқеии худро аз console.anthropic.com гузоред
CLAUDE_MODEL=claude-sonnet-4-6
```

Агар `ANTHROPIC_API_KEY` холӣ монад, ҳамаи платформа кор мекунад, фақат AI чат хато медиҳад (паёми хато дар чат нишон дода мешавад).

## 3. Оғоз кардани сервер

```bash
python app.py
```

Дар бори аввал base де-данных ва маълумоти демо худкор сохта мешаванд (`instance/eduplatform.db`). Сервер дар **http://localhost:5000** кор мекунад.

## 4. Воридшавии демо

| Нақш    | Имейл              | Парол    |
|---------|--------------------|----------|
| Админ   | admin@edu.tj       | admin123 |
| Хонанда | bahora@edu.tj      | 123456   |
| Хонанда | sarvar@edu.tj      | 123456   |

## Сохтори лоиҳа

```
eduplatform/
├── app.py              # Ҳамаи route-ҳои Flask (API + саҳифаҳо)
├── models.py            # Моделҳои SQLAlchemy (User, Topic, Video, Test, Task...)
├── config.py            # Танзимот, .env хониш мешавад
├── requirements.txt
├── .env                  # (худатон месозед — дар .gitignore)
├── .env.example
├── instance/
│   └── eduplatform.db   # SQLite база (худкор сохта мешавад)
├── uploads/              # Видеоҳои бор кардашуда (файли воқеӣ)
├── static/
│   ├── css/style.css
│   └── js/api.js         # fetch() helper-ҳо барои фронтенд
└── templates/
    ├── index.html
    ├── login.html
    ├── admin.html
    ├── pupil.html
    └── chat.html
```

## API Endpoints (хулоса)

**Auth**
- `POST /api/auth/login` — `{email, password}` → сессия
- `POST /api/auth/logout`
- `GET  /api/auth/me`

**Users (admin)**
- `GET  /api/users` — рӯйхати хонандагон
- `POST /api/users` — `{name, email, password}`
- `DELETE /api/users/<id>`

**Topics**
- `GET/POST /api/topics`, `DELETE /api/topics/<id>`

**Videos** (`multipart/form-data`: `title`, `topic_id`, `video`)
- `GET/POST /api/videos`, `DELETE /api/videos/<id>`
- Видео тавассути `/uploads/<filename>` хизмат дода мешавад

**Tests**
- `GET/POST /api/tests`, `GET/DELETE /api/tests/<id>`
- `POST /api/tests/<id>/submit` — `{answers: {"0": 1, "1": 2, ...}}`

**Tasks**
- `GET/POST /api/tasks`, `DELETE /api/tasks/<id>`
- `POST /api/tasks/<id>/submit` — `{answer: "матн"}`

**Chat**
- `GET/POST /api/chat/group` — чати гурӯҳии умумӣ
- `GET /api/chat/ai/history`, `POST /api/chat/ai` — `{message: "..."}` (ба Claude занг мезанад)

## Эзоҳҳои муҳим

- **Бехатарӣ**: парол бо `werkzeug.security` hash карда захира мешавад (на матни оддӣ).
- **Сессия**: Flask session (cookie-based) истифода мешавад — браузер бояд cookies-ро қабул кунад.
- **Видео**: ҳаҷми ҳадди аксар 500MB (дар `config.py` тағйир дода мешавад).
- **Production**: барои истифодаи воқеӣ, `debug=False` гузоред ва тавассути Gunicorn/uWSGI пушт аз Nginx кор кунонед, на `flask run`.
