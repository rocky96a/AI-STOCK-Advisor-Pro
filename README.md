# JOYMAATARA — AI Stock Dashboard

Flask + ML-powered stock analysis dashboard, with a token-based login gate:
no `/api/*` route responds until a user has authenticated.

---

## 1. Run it locally

```bash
# from inside this folder (the one with app.py)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

python3 app.py
```

Open **http://localhost:5000** — you'll land on the login boot screen.

**Default login:** `admin` / `admin123` (auto-created on first run in
`backend/data/users.db`). Change the password or register a new account
from the login page, then remove the `admin` account once you've done so.

---

## 2. Push this to GitHub

From inside this project folder:

```bash
git init
git add .
git commit -m "Initial commit: JOYMAATARA dashboard with login"

# create an empty repo on github.com first, then:
git remote add origin https://github.com/<your-username>/<your-repo>.git
git branch -M main
git push -u origin main
```

Note what's **excluded** by `.gitignore` on purpose (see that file):
- `backend/data/users.db` — contains password hashes, never commit this
- `backend/data/cache/*` and `backend/ml/models/*.pkl` — regenerate these
  via the app itself (`/api/train/<symbol>`) rather than committing large
  binaries to git. If you *do* want to version them, use
  [Git LFS](https://git-lfs.com/).
- `venv/` / `.env` — local-only

---

## 3. Deploy to a live server

The app is already deploy-ready: it binds to `0.0.0.0`, reads `PORT` from
the environment, and ships with a `Procfile` for gunicorn.

### Option A — Render.com (easiest, has a free tier)

1. Push the repo to GitHub (step 2 above).
2. On [render.com](https://render.com) → **New +** → **Web Service** →
   connect your GitHub repo.
3. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
     (Render also auto-detects the `Procfile`, so this may already be filled in.)
4. **Environment variables** (Render dashboard → Environment):
   - `SECRET_KEY` = a long random string — **required**, see warning below.
   - `FLASK_DEBUG` = `false`
5. Deploy. Render gives you a live `https://your-app.onrender.com` URL.

> Note: `torch` + `transformers` + `tensorflow` in `requirements.txt` make
> this a multi-GB install — free tiers may be slow to build or run low on
> memory. If you don't actually use FinBERT sentiment or the LSTM model,
> consider removing those three lines from `requirements.txt` to speed up
> deploys.

### Option B — Railway.app

Same idea as Render: connect the GitHub repo, it reads the `Procfile`
automatically, set the same environment variables in Railway's dashboard.

### Option C — Your own VPS (DigitalOcean, EC2, etc.)

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export FLASK_DEBUG=false

gunicorn app:app --bind 0.0.0.0:5000 --workers 2 --timeout 120
```

Put nginx in front of it for TLS/HTTPS and a real domain, and run gunicorn
under `systemd` (or `pm2`, `supervisor`) so it restarts on crash/reboot.

---

## ⚠️ Critical: set `SECRET_KEY` in production

`backend/auth/token_service.py` signs login tokens with `SECRET_KEY`. If
you don't set it as an environment variable, the app generates a random
one **per process** — meaning:

- Every server restart invalidates all logged-in users' tokens.
- If you run more than one worker/instance (gunicorn `--workers 2`, or
  multiple server instances), each process gets a *different* key, so a
  token issued by one worker will randomly fail on another. Users get
  logged out mid-session for no visible reason.

Fix: always set `SECRET_KEY` explicitly wherever this runs:

```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

Generate it once, save it somewhere safe, and reuse the same value every
time you set the environment variable — don't regenerate it on every
deploy.

---

## Project structure (relevant to auth)

```
backend/auth/
  user_store.py     SQLite user storage (password hashes only)
  token_service.py  Signs/verifies login tokens (needs SECRET_KEY)
  decorators.py     @token_required - gates every API route
  routes.py         /api/auth/login, /register, /logout, /me

static/js/
  auth-guard.js     Redirects to /login if no token; apiFetch() wrapper
  login.js          Boot animation + login/register form logic
  header-auth.js     Header profile/logout wiring

templates/
  login.html        Boot sequence + login/register UI
```
