# MARLO CMS

A full-stack Content Management System built with Django 5, PostgreSQL, Django Templates, DRF + JWT. Sky-blue admin dashboard with Cloudinary media storage.

---

## Tech Stack
- **Backend**: Django 5 + Django REST Framework
- **Database**: PostgreSQL 16
- **Auth**: Session auth (templates) + JWT (API / AJAX)
- **Media**: Cloudinary
- **Frontend**: Django Templates
- **Deployment**: Render (backend + DB) | Cloudinary (media)

---

## Local Setup

### 1. Clone and create virtual environment
```bash
git clone <your-repo-url>
cd marlo_cms
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create PostgreSQL database
```bash
createdb marlo_db
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your values
```

Key values to fill in `.env`:
```
SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=True
DB_NAME=marlo_db
DB_USER=postgres
DB_PASSWORD=yourpassword
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

### 4. Run migrations and create superuser
```bash
python manage.py migrate
python manage.py createsuperuser
# Use email as the username when prompted
```

### 5. Collect static files and run
```bash
python manage.py collectstatic --no-input
python manage.py runserver
```

Visit: http://localhost:8000

---

## Cloudinary Setup (Free)

1. Sign up at https://cloudinary.com
2. Go to Dashboard → copy Cloud Name, API Key, API Secret
3. Paste into your `.env`

---

## Deploy to Render

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/your-username/marlo-cms.git
git push -u origin main
```

### Step 2 — Create Render Web Service
1. Go to https://render.com → New → Web Service
2. Connect your GitHub repo
3. Set:
   - **Build command**: `./build.sh`
   - **Start command**: `gunicorn marlo_cms.wsgi:application --bind 0.0.0.0:$PORT`
   - **Runtime**: Python 3

### Step 3 — Add PostgreSQL on Render
1. New → PostgreSQL
2. Copy the **Internal Database URL**
3. Add it as environment variable: `DATABASE_URL`

### Step 4 — Set Environment Variables on Render
Add these in the Render dashboard → Environment:
```
SECRET_KEY=<your-secret-key>
DEBUG=False
ALLOWED_HOSTS=your-app.onrender.com
DATABASE_URL=<from Render postgres>
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
CORS_ALLOWED_ORIGINS=https://your-app.onrender.com
```

### Step 5 — Deploy
Render will auto-deploy on every push to `main`.
After first deploy, create a superuser via Render shell:
```bash
python manage.py createsuperuser
```

---

## Pages

| URL | Description |
|-----|-------------|
| `/` | Blog post listing |
| `/post/<slug>/` | Post detail with comments + like |
| `/about/` | About page |
| `/register/` | User registration |
| `/login/` | Login |
| `/profile/` | Edit profile |
| `/dashboard/` | Admin dashboard home |
| `/dashboard/posts/` | Manage posts |
| `/dashboard/posts/create/` | Create post |
| `/dashboard/users/` | Manage users |
| `/dashboard/comments/` | Moderate comments |

## REST API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/register/` | Register user |
| POST | `/api/auth/token/` | Get JWT tokens |
| POST | `/api/auth/token/refresh/` | Refresh token |
| GET | `/api/posts/` | List posts |
| GET | `/api/posts/<slug>/` | Post detail |
| POST | `/api/comments/post/<slug>/` | Submit comment |
| PATCH | `/api/comments/<id>/` | Moderate comment (admin) |
| POST | `/api/interactions/like/<slug>/` | Like / unlike post |

---

## Project Structure
```
marlo_cms/
├── marlo_cms/          # Django project config
├── apps/
│   ├── accounts/       # Users, auth, JWT
│   ├── posts/          # Blog posts, attachments
│   ├── comments/       # Comments, moderation
│   └── interactions/   # Likes, read counts
├── templates/          # All HTML templates
│   ├── base.html
│   ├── accounts/
│   ├── posts/
│   └── dashboard/
├── static/
│   ├── css/style.css   # Sky-blue design system
│   └── js/main.js      # Like + comment AJAX
├── requirements.txt
├── Procfile
└── build.sh
```
