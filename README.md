<div align="center">

# AI Notes by ZeroTrace

### An open-source, AI-powered note-taking app built with Python & Flask

Capture, organize, and manage your notes with a fast, clean, developer-focused interface.
Summarize, expand, and rewrite any note with built-in AI — no plugins, no bloat.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20Framework-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![OpenAI](https://img.shields.io/badge/AI-OpenAI%20GPT--4o--mini-412991?logo=openai&logoColor=white)](https://platform.openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Deploy to Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)](https://render.com/)

**Status:** V1 · Self-hosted · MIT Licensed

</div>

---

## Table of contents

- [What is AI Notes?](#what-is-ai-notes)
- [Keywords & topics](#keywords--topics)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Screenshots](#screenshots)
- [Getting started (local setup)](#getting-started-local-setup)
- [Environment variables](#environment-variables)
- [Deployment on Render](#deployment-on-render)
- [Project structure](#project-structure)
- [API reference](#api-reference)
- [Database schema](#database-schema)
- [Frequently asked questions](#frequently-asked-questions)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## What is AI Notes?

**AI Notes by ZeroTrace** is an open-source, self-hosted **AI note-taking app** powered by **Python and Flask**. It is the first release (V1) of the ZeroTrace Workflow AI platform — a productivity suite for developers, students, and teams who want a fast, privacy-friendly alternative to heavy SaaS note tools.

Unlike traditional note apps, AI Notes ships with an **AI assistant** that can summarize, expand, and rewrite your notes using **OpenAI GPT-4o-mini** — directly inside your workflow. Notes are stored locally in **SQLite**, so you keep full ownership of your data.

Whether you are looking for a **free note-taking app**, a **self-hosted notes server**, a **Flask notes app with a REST API**, or a **base project for an AI productivity tool**, AI Notes is a clean, hackable starting point.

> **Live:** V1 is deployed and reachable via a Render web service.

---

## Keywords & topics

`ai notes app` · `ai note taking app` · `open source notes app` · `self-hosted notes` · `flask notes app` · `python note taking app` · `openai gpt-4o-mini` · `ai summarizer` · `note summarization` · `markdown notes` · `rest api` · `sqlite` · `zero trace ai` · `productivity app` · `note manager` · `flask rest api` · `render deployment`

---

## Features

- **AI note assistant** — summarize, expand, and rewrite notes with OpenAI (`GPT-4o-mini`), capped at 10 actions per user per day.
- **Full note CRUD** — create, edit, read, and delete notes through the UI or the REST API.
- **Real-time search** — instant filtering across titles and content.
- **Tags & colors** — organize notes with colored tags and filter by tag.
- **Pin, sort & organize** — pin important notes and sort by newest, oldest, or alphabetical order.
- **Trash & restore** — soft-delete with a recycle bin, restore, or permanently empty the trash.
- **Rich content** — plain and Markdown note formats with a built-in rich text editor.
- **User accounts & sessions** — signup, signin, secure session handling, and email verification tokens.
- **Rate limiting** — brute-force protection on authentication (5 attempts / 15 minutes).
- **Export & import** — back up all notes to JSON and import them back, including tags.
- **Superadmin dashboard** — user, note, and waitlist analytics with per-day charts.
- **Waitlist landing page** — collect early-access signups before launch.
- **FSCSS styling engine** — a custom pure-Python CSS preprocessor with variables, shorthands, mixins, and nesting.
- **Responsive dark UI** — desktop, tablet, and mobile layouts with a modern purple-accented dark theme.
- **RESTful API** — every operation is available as a documented JSON endpoint.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3, Flask (blueprints) |
| **Database** | SQLite (auto-migrating, auto-seeding) |
| **AI** | OpenAI Chat Completions API (`gpt-4o-mini`) |
| **Frontend** | HTML5, JavaScript, FSCSS |
| **Styling engine** | FSCSS — a custom pure-Python CSS preprocessor |
| **Auth** | Flask sessions + SHA-256 password hashing |
| **Server** | Gunicorn (production WSGI) |
| **Hosting** | Render |

---

## Screenshots

> Screenshots are added as each page is rebuilt. Placeholders below.

| Landing page | Notes app | Superadmin dashboard |
|:---:|:---:|:---:|
| _coming soon_ | _coming soon_ | _coming soon_ |

---

## Getting started (local setup)

### Prerequisites

- Python 3.10 or newer
- `pip` and `venv`
- (Optional) An OpenAI API key for AI features

### 1. Clone the repository

```bash
git clone https://github.com/Omonire/zerotrace-ai-notes.git
cd zerotrace-ai-notes
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` (see [Environment variables](#environment-variables)).

### 5. Run the app

```bash
python app.py
```

Open **http://localhost:5000**.

> The superadmin dashboard is at `/superadmin` and is secured by `SUPERADMIN_USERNAME` / `SUPERADMIN_PASSWORD` from the environment — no DB account is seeded.

---

## Environment variables

Create a `.env` file in the project root:

| Variable | Required | Description |
|----------|:--------:|-------------|
| `SECRET_KEY` | ✅ | Flask session signing key. Use a long random string. |
| `FLASK_DEBUG` | ➖ | `true` for local dev, `false` in production. |
| `OPENAI_API_KEY` | ⚪ | Enables the AI summarize/expand/rewrite features. |
| `SUPERADMIN_USERNAME` | ⚪ | Username for the `/superadmin` login (default `superadmin`). |
| `SUPERADMIN_PASSWORD` | ⚪ | Password for the `/superadmin` login. Ignored/disabled when empty. |
| `DATABASE_PATH` | ⚪ | Custom SQLite path (e.g. `/var/data/AI_Notes.db` on Render). Defaults to `AI_Notes.db` next to the source. |

```env
SECRET_KEY=change-this-to-a-random-string
OPENAI_API_KEY=sk-your-key-here
FLASK_DEBUG=false
SUPERADMIN_USERNAME=superadmin
SUPERADMIN_PASSWORD=change-this-superadmin-password
```

---

## Deployment on Render

Render builds directly from a Git repo and runs the app behind a production WSGI server.

### Prerequisites

- Push the repo to GitHub (or GitLab/Bitbucket).
- Ensure `gunicorn` is listed in `requirements.txt`.

### Steps

1. Push your code to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), click **New → Web Service** and connect your repo.
3. Configure the service:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Add environment variables (Environment tab):

   | Key | Value |
   |-----|-------|
   | `SECRET_KEY` | a long random string (do not reuse the dev value) |
   | `FLASK_DEBUG` | `false` |
   | `OPENAI_API_KEY` | optional, required for AI features |

5. Click **Create Web Service**. Render builds and deploys; your app is live at `https://<service-name>.onrender.com`.

### Persistent database (SQLite caveat)

Render's default filesystem is **ephemeral**, so `AI_Notes.db` is wiped on every deploy and restart. To keep data:

1. Under **Settings → Disks**, add a disk (e.g. mount path `/var/data`).
2. Point the app at it, e.g. set `DATABASE_PATH=/var/data/AI_Notes.db`.

> `database.py` reads `DATABASE_PATH` from the environment, so pointing it at the mounted disk (e.g. `DATABASE_PATH=/var/data/AI_Notes.db`) is all that is required.

For a production workload, consider migrating to a managed Postgres instance instead of SQLite.

---

## Project structure

```
zerotrace-ai-notes/
├── app.py                  # Main Flask app: pages, notes, AI, tags, settings
├── database.py             # SQLite setup & migrations
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── API.md                  # Full REST API reference
│
├── auth/                   # Authentication blueprint
│   ├── __init__.py         # Blueprint definition
│   ├── CREATE/
│   │   ├── create_username.py
│   │   └── create_password.py
│   └── GET/
│       ├── get_username.py
│       └── get_password.py
│
├── fscss/                  # FSCSS styling engine
│   ├── compiler.py         # Pure-Python .fscss → .css compiler
│   ├── __init__.py         # Flask blueprint serving compiled CSS
│   └── __main__.py         # CLI entry point
│
├── templates/              # Jinja2 HTML pages
│   ├── landing.html        # Public landing page
│   ├── waitlist.html       # Early-access waitlist
│   ├── signup.html         # Sign up
│   ├── signin.html         # Sign in
│   ├── verify.html         # Email verification
│   ├── demo_index.html     # Main notes application
│   ├── trash.html          # Recycle bin
│   ├── settings.html       # User settings
│   └── superadmin.html     # Superadmin dashboard
│   └── superadmin_login.html # Superadmin login
│
└── static/
    ├── css/
    │   ├── style.fscss     # Source styles (FSCSS)
    │   └── style.css       # Compiled CSS
    └── js/
        └── script.js       # Client-side logic
```

---

## API reference

All `POST`/`PUT` endpoints accept `Content-Type: application/json` and return JSON with a `success` boolean. See **[API.md](API.md)** for full request/response examples.

### Pages

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Landing page |
| `GET` | `/app` | Notes application |
| `GET` | `/waitlist` | Waitlist signup |
| `GET` | `/superadmin` | Superadmin login + dashboard |

### Notes

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/notes` | List notes (supports `?search=`, `?sort=`, `?tag=`) |
| `GET` | `/api/notes/<id>` | Get a single note |
| `POST` | `/api/notes` | Create a note |
| `PUT` | `/api/notes/<id>` | Update a note |
| `DELETE` | `/api/notes/<id>` | Move a note to trash |
| `PUT` | `/api/notes/<id>/pin` | Toggle pin |
| `PUT` | `/api/notes/<id>/restore` | Restore from trash |
| `DELETE` | `/api/notes/<id>/permanent` | Permanently delete |
| `GET` | `/api/notes/export` | Export all notes as JSON |
| `POST` | `/api/notes/import` | Import notes from JSON |

### AI

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/ai/summarize` | Summarize note content |
| `POST` | `/api/ai/expand` | Expand note content |
| `POST` | `/api/ai/rewrite` | Rewrite note content |
| `GET` | `/api/ai/usage` | Get today's AI usage |

### Auth, tags & settings

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/signup` | Create an account |
| `POST` | `/api/signin` | Sign in |
| `POST` | `/api/verify-email` | Verify email token |
| `GET` | `/api/tags` | List tags |
| `POST` | `/api/tags` | Create a tag |
| `DELETE` | `/api/tags/<id>` | Delete a tag |
| `PUT` | `/api/settings/username` | Update username |
| `PUT` | `/api/settings/password` | Update password |
| `GET` | `/api/settings/stats` | Get user stats |

---

## Database schema

| Table | Purpose |
|-------|---------|
| `notes` | Note title, content, format, pin/trash state, timestamps |
| `users` | Username, email, hashed password, admin flag, verification |
| `tags` | Per-user tags with colors |
| `note_tags` | Many-to-many link between notes and tags |
| `ai_usage` | Per-user AI action and token tracking |
| `waitlist` | Early-access signups (name, email) |
| `login_attempts` | Rate-limiting audit for sign-in attempts |

---

## Frequently asked questions

**Is AI Notes free and open source?**
Yes. AI Notes is released under the MIT license and can be self-hosted at no cost.

**What do I need to run the AI features?**
An OpenAI API key (`OPENAI_API_KEY`). Without it, all non-AI features work normally.

**Where is my data stored?**
Notes are stored in a local SQLite database (`AI_Notes.db`). You own your data.

**Can I deploy it for free?**
Yes — the repo is configured for one-click deployment on Render's free tier.

**Which model does the AI use?**
OpenAI `gpt-4o-mini` via the Chat Completions API.

**Can I use it without OpenAI?**
Yes. AI features simply return a "not configured" message; everything else works.

---

## Roadmap

- [ ] V2: richer AI workflows and prompt templates
- [ ] Note sharing and collaboration
- [ ] Categories and nested notebooks
- [ ] Full-text search with ranking
- [ ] Postgres support for production scaling
- [ ] Automated test suite and CI

---

## Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`.
3. Commit your changes: `git commit -m "Add my feature"`.
4. Push the branch: `git push origin feature/my-feature`.
5. Open a Pull Request.

Please keep pull requests focused and match the existing code style.

---

## License

Released under the **MIT License**. See [LICENSE](LICENSE) for details.

<div align="center">

**AI Notes by ZeroTrace** — built with Python, Flask, and a little bit of AI.

[⭐ Star this repo](https://github.com/Omonire/zerotrace-ai-notes) · [🐛 Report an issue](https://github.com/Omonire/zerotrace-ai-notes/issues) · [🍴 Fork it](https://github.com/Omonire/zerotrace-ai-notes/fork)

</div>
