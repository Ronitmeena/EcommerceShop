# Flask E‑Commerce 

A clean, recruiter‑friendly Flask e‑commerce app with:
- Product listing with **search** and **category filter**
- **Cart with item count** in navbar (session‑based)
- **Checkout** that stores orders
- **Auth** (register/login/logout) with **bcrypt password hashing**
- Bootstrap UI with product cards and images

## 1) Quickstart 

```bash
# 1. Create and activate a virtual env (Windows PowerShell shown; adapt for Linux/macOS)
python -m venv .venv
. .venv/Scripts/Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) set env vars
copy .env.example .env   # on Linux/macOS: cp .env.example .env

# 4. Initialize DB and seed sample data
python -c "from app import app, db; 
from flask.cli import ScriptInfo"  # ignore output, ensures imports work
flask --app app init-db
flask --app app seed

# 5. Run
flask --app app run --debug
```

Open http://127.0.0.1:5000

## 2) Project Structure
```
ecommerce_flask/
  app.py
  requirements.txt
  Procfile
  .env.example
  templates/
    base.html, index.html, product_detail.html, cart.html, checkout.html
    login.html, register.html
  static/styles.css
```

## 3) What to Showcase in README
- Short description of features and tech stack
- Screenshots (homepage, product detail, cart, checkout)
- If deployed, add **Live Demo** link

## 4) Deployment (Render, free tier)
- Create a new **Web Service** on Render
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `gunicorn app:app`
- **Environment**: set `SECRET_KEY` to a random string
- Add a **Persistent Disk** or let SQLite create `app.db` on ephemeral storage
- After first deploy, run once in the Render Shell:
  ```bash
  flask --app app init-db
  flask --app app seed
  ```

