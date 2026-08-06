# Gixvor Mail Fetcher

A Django web app that connects to any Gmail inbox over IMAP and pulls
every message sent by one particular sender — parsed, cached, and laid
out in a clean dashboard instead of a raw email client.

Built as a self-contained demo of a real-world integration: secure
credential handling, MIME parsing, a cached data model, and a
from-scratch front end (no CSS framework).

## Features

- **Sender-scoped search** — runs a real IMAP `SEARCH FROM "<sender>"`
  against Gmail, so the filtering happens server-side, not by scanning
  every message.
- **Full MIME parsing** — multipart-safe extraction of subject, sender,
  recipient, date, plain-text body (with HTML-to-text fallback), and
  attachment names, including encoded headers.
- **Expandable results UI** — envelope-style cards that expand inline,
  plus a dedicated page per message.
- **Search history & refresh** — every search is cached to SQLite so
  results can be revisited, and a one-click Refresh re-pulls the
  latest mail without retyping anything.
- **No credentials in the database** — see [Security](#security) below.
- **Demo/seed mode** — populate the UI with realistic fake data via
  `python manage.py seed_demo`, so it can be reviewed or screenshotted
  without connecting any real inbox.

## Tech stack

Python 3.10+ · Django 5 · `imaplib` / `email` (standard library) ·
SQLite · Gunicorn + WhiteNoise (production) · plain CSS/JS, no
front-end framework or build step.

## Security

This app asks for a Gmail **App Password**, a sensitive credential, so
it's designed to hold as little of it as possible:

- Sent to Gmail only over `IMAP_SSL` (TLS-encrypted).
- Kept **only in the server-side session**, never written to a
  database table.
- Sessions use Django's in-memory cache backend
  (`SESSION_ENGINE = "django.contrib.sessions.backends.cache"`)
  rather than the framework default of storing sessions in the
  database — so the password only ever exists in server RAM, and is
  gone the moment the process restarts.
- Sessions expire after 30 minutes or when the browser closes; a
  **Disconnect** button clears it immediately.
- Each visitor uses their **own** Gmail address and App Password —
  nothing is shared or pre-configured, and nothing here can access an
  account without its owner generating and entering that App Password
  themselves.

If you deploy this publicly, also review the [Deployment](#deployment)
checklist below (`DEBUG=False`, a real `SECRET_KEY`, HTTPS).

## Local setup

\`\`\`bash
git clone <your-fork-or-repo-url>
cd gixvor-gmail-fetcher

python3 -m venv venv
source venv/bin/activate          # Windows: venv\\Scripts\\activate

pip install -r requirements.txt
cp .env.example .env

python manage.py migrate
python manage.py runserver
\`\`\`

Open `http://127.0.0.1:8000/`. To try it without a real inbox:

\`\`\`bash
python manage.py seed_demo
\`\`\`

This prints a URL straight to a results page pre-filled with fake
sample emails.

To try it with a real Gmail inbox, click **Connect an inbox** and
you'll need:
1. IMAP enabled: Gmail → Settings → *See all settings* → *Forwarding
   and POP/IMAP* → enable IMAP access.
2. 2-Step Verification on: `myaccount.google.com/security`.
3. An App Password: `myaccount.google.com/apppasswords` → generate one
   → paste it into the app (it is **not** your normal Gmail password).

## Deployment

These steps work on most PaaS providers with a Python buildpack
(Render, Railway, Heroku, Fly.io). Example using **Render**:

1. Push this repo to GitHub.
2. On Render: **New → Web Service** → connect the repo.
3. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
4. Start command: `gunicorn gmailfetcher.wsgi`
5. Set environment variables:
   - `DJANGO_SECRET_KEY` — generate one, e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`
   - `DJANGO_DEBUG` = `False`
   - `DJANGO_ALLOWED_HOSTS` = `your-app.onrender.com`
   - `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://your-app.onrender.com`
6. Deploy. Render (and similar platforms) runs migrations automatically
   via the included `Procfile`'s `release` step; if your platform
   doesn't support that, run `python manage.py migrate` manually once
   after the first deploy.

A `Procfile` and `whitenoise`-based static file serving are already
included, so no extra static-file infrastructure (S3, CDN, etc.) is
required to deploy.

## Project layout

\`\`\`
gixvor-gmail-fetcher/
├── manage.py
├── requirements.txt
├── Procfile                 # for PaaS deployment
├── .env.example
├── gmailfetcher/             # Django project (settings, urls, wsgi)
└── fetcher/                  # the app
    ├── gmail_client.py       # IMAP connection + MIME parsing
    ├── models.py              # SearchQuery / CachedEmail (no passwords stored)
    ├── forms.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── management/commands/seed_demo.py   # fake-data seeding for demos
    ├── templates/fetcher/     # landing, connect, results, detail, history
    └── static/fetcher/        # style.css, app.js
\`\`\`

## Troubleshooting

- **"Gmail rejected that address/App Password combination"** — confirm
  you're using a 16-character App Password (not your login password)
  and that IMAP is enabled in Gmail settings.
- **No messages found** — Gmail's `FROM` search matches on the raw
  header; try the bare email address rather than a display name, and
  double-check the mailbox/label name if it isn't the default Inbox.
- **`no such table` errors locally** — run `python manage.py migrate`
  (and `python manage.py makemigrations fetcher` first if you've
  changed the models).
