# Render Deployment

Create a Render Web Service with `backend/` as its root directory.

- Build command: `npm --prefix ../frontend ci && npm --prefix ../frontend run build && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py ensure_admin`
- Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

Set these private environment variables in Render:

- `DATABASE_URL`: PostgreSQL connection URL from Neon.
- `DJANGO_SECRET_KEY`: a new, long random secret.
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS`: the Render hostname without `https://`.
- `DJANGO_ADMIN_EMAIL`, `DJANGO_ADMIN_PASSWORD`, and optionally `DJANGO_ADMIN_USERNAME`.
- `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_WEBHOOK_SECRET`, and `MERCADOPAGO_WEBHOOK_URL`.
- `FRONTEND_URL`: the public HTTPS Render URL.

`ensure_admin` runs on every deployment. It creates the administrator on the first deployment and keeps its password and staff privileges synchronized with the configured environment variables.

The Render service compiles `frontend/` and serves it from Django. This keeps the frontend and API on the same origin, which allows the HttpOnly refresh cookie to work without cross-origin configuration.
