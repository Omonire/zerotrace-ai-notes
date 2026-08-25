# AI Notes by ZeroTrace

The first step toward a smarter workflow platform. Capture, organize, and manage your notes with a clean, developer-focused interface.

**Live Status:** V1 deployed

## What is this?

AI Notes is V1 of the ZeroTrace Workflow AI platform. It's a note-taking app built for developers who want a fast, clean interface without the bloat. This version focuses on core CRUD functionality. AI-powered features are coming in V2.

## Features

- Create, edit, and delete notes
- Search notes in real time
- Responsive design (desktop, tablet, mobile)
- Dark theme with purple accent
- Waitlist system for early access signups
- User authentication module (username/password)
- RESTful API for all operations

## Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS (FSCSS), JavaScript
- **Auth:** SHA-256 password hashing

## Project Structure

```
zerotrace-ai-notes/
├── app.py                  # Main Flask application, routes
├── database.py             # SQLite setup, table creation
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not committed)
├── .gitignore              # Ignored files
├── AI_Notes.db             # SQLite database (not committed)
│
├── auth/                   # Authentication module
│   ├── __init__.py         # Blueprint definition
│   ├── CREATE/
│   │   ├── create_username.py
│   │   └── create_password.py
│   └── GET/
│       ├── get_username.py
│       └── get_password.py
│
├── templates/
│   ├── landing.html        # Landing page (public)
│   ├── waitlist.html       # Waitlist signup page
│   └── demo_index.html     # Main notes app
│
└── static/
    ├── css/
    │   ├── style.fscss     # Source styles (FSCSS)
    │   └── style.css       # Compiled CSS fallback
    └── js/
        └── script.js       # Client-side logic
```

## Routes

### Pages

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Landing page |
| GET | `/app` | Notes application |
| GET | `/waitlist` | Waitlist signup |

### API - Notes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/notes` | List all notes (supports `?search=`) |
| GET | `/api/notes/<id>` | Get single note |
| POST | `/api/notes` | Create note (JSON body: `title`, `content`) |
| PUT | `/api/notes/<id>` | Update note (JSON body: `title`, `content`) |
| DELETE | `/api/notes/<id>` | Delete note |

### API - Waitlist

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/waitlist` | Join waitlist (JSON body: `name`, `email`) |

### API - Auth

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/create_username` | Create user (JSON body: `username`) |
| POST | `/api/create_password` | Set password (JSON body: `username`, `password`) |
| GET | `/api/get_username` | Get user info (query param: `username`) |
| GET | `/api/get_password` | Check if user has password (query param: `username`) |

### Form

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/notes/save` | Create note via form (redirects to `/app`) |

## Local Setup

```bash
git clone https://github.com/Omonire/zerotrace-ai-notes.git
cd zerotrace-ai-notes
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`

## Environment Variables

Create a `.env` file:

```
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=true
```

## Deployment (PythonAnywhere)

1. Clone repo on PythonAnywhere Bash console
2. Create virtualenv and install dependencies
3. Add new web app (Manual config, Python 3.10)
4. Set working directory to project folder
5. Edit WSGI file:

```python
import sys
project_home = '/home/your-username/zerotrace-ai-notes'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
from app import app as application
```

6. Reload web app

## Database Schema

### notes
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, autoincrement |
| title | TEXT | Note title |
| content | TEXT | Note body |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |

### waitlist
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, autoincrement |
| name | TEXT | User's name |
| email | TEXT | User's email (unique) |
| created_at | TIMESTAMP | Signup time |

### users
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, autoincrement |
| username | TEXT | Username (unique) |
| password | TEXT | SHA-256 hashed password |
| created_at | TIMESTAMP | Creation time |

## What's Next (V2)

- AI-powered note summarization
- Note tagging and categories
- Full user authentication with sessions
- Note sharing and collaboration
- Workflow automation engine

## License

MIT
