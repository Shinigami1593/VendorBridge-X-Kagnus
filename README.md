# VendorBridge X Kagnus - Week 1

Procurement and vendor management app.
Stack: Vue 3 (Vite) + Django REST Framework + SQLite.

## Features
- Register, login, logout, forgot/reset password
- 4 roles: Admin, Procurement Officer, Manager, Vendor
- Dashboard with summary cards and empty states
- Vendor management: add, view, edit, delete, search, status filter

## What you need
- Python 3.12 or newer
- Node.js 18 or newer

## Run the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```
SECRET_KEY=put-a-long-random-text-here
DEBUG=True
ALLOWED_HOSTS=*
CORS_ORIGINS=http://localhost:5173
FRONTEND_URL=http://localhost:5173
```

Then run:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API runs at http://127.0.0.1:8000

To make the first Admin: open http://127.0.0.1:8000/admin/, log in with the
superuser, open your user, and set Role to Admin.

Make a secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## Run the frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```
VITE_API_URL=http://127.0.0.1:8000/api
```

Then run:

```bash
npm run dev
```

Open http://localhost:5173

## Environment variables

| File | Name | What it is |
|------|------|------------|
| backend/.env | SECRET_KEY | Django secret key |
| backend/.env | DEBUG | True for local, False for live |
| backend/.env | ALLOWED_HOSTS | Allowed host names |
| backend/.env | CORS_ORIGINS | Frontend address(es), comma separated |
| backend/.env | FRONTEND_URL | Used in the password reset link |
| backend/.env | DATABASE_URL | Optional. Uses SQLite if empty |
| frontend/.env | VITE_API_URL | Backend API address |

## Roles

| Role | Dashboard | View vendors | Add / Edit | Delete |
|------|-----------|--------------|------------|--------|
| Admin | Yes | Yes | Yes | Yes |
| Procurement Officer | Yes | Yes | Yes | No |
| Manager | Yes | Yes | No | No |
| Vendor | No | No | No | No |

Admin cannot be chosen on the register page. It is set in the Django admin.
Roles are checked on the backend.

## Tests

```bash
cd backend
python manage.py test
```

## Password reset (local)

Emails print in the backend terminal. Copy the link from there.

## Known limitations
- Sidebar modules for later weeks show "coming soon".
- Login tokens do not expire.
- No real email service yet.
- Vendor role has no portal yet.
- Not deployed.

## Screenshots
See the `screenshots/` folder.
