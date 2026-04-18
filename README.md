# Finity — Personal Finance Tracker

A full-stack personal finance tracker with a **FastAPI (Python)** backend, **PostgreSQL** database, and a pure HTML/CSS/JS frontend. Deployable on Render for free.

```
finity/
├── finance-backend/          ← Python FastAPI backend
│   ├── src/
│   │   ├── db/
│   │   │   ├── database.py   ← DB connection + init
│   │   │   └── schema.sql    ← PostgreSQL schema
│   │   ├── middleware/
│   │   │   └── auth.py       ← JWT authentication
│   │   ├── routes/
│   │   │   ├── auth.py       ← /api/auth/register, /login
│   │   │   ├── transactions.py ← /api/transactions CRUD
│   │   │   └── budgets.py    ← /api/budgets CRUD
│   │   └── index.py          ← FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── finance-frontend/
│   └── index.html            ← Complete single-page frontend
└── README.md
```

---

## Local Development

### 1. Prerequisites
- Python 3.11+
- PostgreSQL (local or use a free Render DB)

### 2. Backend setup

```bash
cd finance-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in DATABASE_URL and JWT_SECRET

# Run the server
uvicorn src.index:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 3. Frontend setup

Update the `API_URL` in `finance-frontend/index.html`:

```js
const API_URL = 'http://localhost:8000';
```

Open `finance-frontend/index.html` in your browser — or serve it:

```bash
cd finance-frontend
python -m http.server 3000
```

---

## Deploying to Render (Free)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit — Finity finance tracker"
git remote add origin https://github.com/YOUR_USERNAME/finity.git
git push -u origin main
```

### Step 2 — Create a PostgreSQL database on Render

1. Go to [render.com](https://render.com) → New → **PostgreSQL**
2. Name: `finity-db` | Plan: **Free**
3. Click **Create Database**
4. Copy the **Internal Database URL** (for the backend service)

### Step 3 — Deploy the Backend (Web Service)

1. Render → New → **Web Service**
2. Connect your GitHub repo
3. Settings:
   - **Name**: `finity-api`
   - **Root Directory**: `finance-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.index:app --host 0.0.0.0 --port $PORT`
4. Add **Environment Variables**:
   ```
   DATABASE_URL   = <paste Internal Database URL from Step 2>
   JWT_SECRET     = <generate: python -c "import secrets; print(secrets.token_hex(32))">
   FRONTEND_URL   = *
   ```
5. Click **Create Web Service**
6. Wait for deploy — copy your backend URL (e.g. `https://finity-api.onrender.com`)

### Step 4 — Update Frontend API URL

In `finance-frontend/index.html`, find this line and update it:

```js
const API_URL = window.API_URL || 'https://finity-api.onrender.com';
//                                  ↑ replace with your actual Render backend URL
```

Commit and push this change:

```bash
git add finance-frontend/index.html
git commit -m "Set production API URL"
git push
```

### Step 5 — Deploy the Frontend (Static Site)

1. Render → New → **Static Site**
2. Connect your GitHub repo
3. Settings:
   - **Name**: `finity-app`
   - **Root Directory**: `finance-frontend`
   - **Build Command**: *(leave empty)*
   - **Publish Directory**: `.`
4. Click **Create Static Site**
5. Your app is live at `https://finity-app.onrender.com` 🎉

---

## API Reference

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register` | Create account | No |
| POST | `/api/auth/login` | Sign in | No |
| GET | `/api/transactions` | List transactions (filter by `month`, `type`) | Yes |
| POST | `/api/transactions` | Add transaction | Yes |
| DELETE | `/api/transactions/{id}` | Delete transaction | Yes |
| GET | `/api/transactions/summary/monthly` | 6-month income/expense summary | Yes |
| GET | `/api/budgets` | Get user's budgets + actuals | Yes |
| PUT | `/api/budgets` | Save/update budget limits | Yes |
| DELETE | `/api/budgets/{category}` | Remove a budget | Yes |
| GET | `/api/health` | Health check | No |

Interactive API docs: `https://your-backend.onrender.com/docs`

---

## Key Features

- ✅ **No sample data** — every user starts fresh, all data is theirs
- ✅ **Persistent** — data survives logout/login, stored in PostgreSQL
- ✅ **User-defined budgets** — set your own monthly limits per category
- ✅ **JWT auth** — secure, stateless authentication
- ✅ **Per-user isolation** — users never see each other's data
- ✅ **Mobile responsive** — works on all screen sizes
- ✅ **AI Assistant** — personalised advice based on your real transactions
