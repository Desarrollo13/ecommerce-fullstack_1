# E-commerce Backend

## Run And Verify

- Run Django commands from `backend/` with the repository's sibling virtual environment: `..\venv\Scripts\python.exe manage.py <command>`.
- Use `..\venv\Scripts\python.exe manage.py check` for a fast configuration check.
- Before committing model changes, run `..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run`; create migrations with `..\venv\Scripts\python.exe manage.py makemigrations <app>` and apply them with `..\venv\Scripts\python.exe manage.py migrate`.
- Run the current app test target with `..\venv\Scripts\python.exe manage.py test users cart orders products`. Tests and database-backed commands require the local MySQL instance configured in `config/settings.py` (`ecommerce_db` on `localhost:3306`).
- Local dependencies are installed in the sibling `venv/`. Production dependencies are pinned in `backend/requirements.txt`; install them locally with `..\venv\Scripts\python.exe -m pip install -r requirements.txt`.
- Run the React frontend from `frontend/` with `npm.cmd run dev`, `npm.cmd run lint`, and `npm.cmd run build`; use `npm.cmd` because PowerShell script execution is disabled on this machine.
- Vite proxies `/api` to `http://127.0.0.1:8000` by default. Production builds use `/static/` as their asset base and Django serves the compiled frontend from the same origin.

## Structure And API Behavior

- `config/settings.py` is the settings source and `config/urls.py` is the HTTP entrypoint. It mounts `products.api.urls` under `/api/`.
- `users.User` is the configured user model. Use `settings.AUTH_USER_MODEL` for new user relations; JWT login identifies users by their unique email address.
- Product and category write permissions use Django's `is_staff` through `IsAdminUser`; the user `role` field does not grant write or Django admin access.
- `cart` owns the authenticated `/api/cart/` endpoints. It has one cart per user and at most one item per product; it validates available stock but does not reserve or decrement it.
- `orders` owns authenticated `/api/orders/` endpoints. Checkout creates immutable product-name and price snapshots, validates stock under row locks, decrements it, and clears the cart in one transaction.
- Keep product and category API endpoints, serializers, and generic views in `products/api/`; data models and their migrations belong in `products/` and `products/migrations/`.
- `/api/products/` and `/api/categories/` expose list/create and detail routes. Reads are public; POST, PUT, PATCH, and DELETE require an authenticated Django staff user through `IsAdminUser`.
- Public registration is `POST /api/auth/register/`; it creates customer users and never accepts a role or staff status.
- JWT access and refresh endpoints are `/api/auth/token/` and `/api/auth/token/refresh/`; access tokens last 15 minutes and refresh tokens one day.
- `Product.category` uses `on_delete=PROTECT`, so category deletion must account for existing products.
- Mercado Pago preferences are created at `POST /api/orders/<id>/payment-preference/`. Sandbox uses an `MERCADOPAGO_ACCESS_TOKEN` beginning with `TEST-`, never a production `APP_USR-` token.
- Configure `MERCADOPAGO_WEBHOOK_SECRET` and `MERCADOPAGO_WEBHOOK_URL` in `.env`. The webhook endpoint is `POST /api/orders/payments/webhook/`; it verifies signed Webhooks and safely handles legacy `topic=payment` notifications by fetching and validating the provider payment.
- A provider payment changes an order only when its external reference and amount match. It stores `provider_payment_id` and maps approved, rejected/cancelled, and refunded/charged-back payments to the internal payment state.
- Set `FRONTEND_URL` only to a public HTTPS frontend URL. When present, payment preferences send users to `<FRONTEND_URL>/payment-result`; localhost is rejected by Mercado Pago when used with `auto_return`.

## Current Integration Status

- The production service is live at `https://ecommerce-api-rysy.onrender.com`. It uses a fresh Neon PostgreSQL database. The initial administrator is created and updated on each deploy by `ensure_admin` from private Render environment variables; never commit those values.
- Render uses `backend/` as its root directory. Its Build Command must compile `../frontend` before `collectstatic`; use the command in `backend/DEPLOYMENT.md`. The Start Command is `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
- The React storefront is served by Django at `/`, and `/payment-result` serves the same SPA entrypoint. This keeps JWT refresh cookies, frontend, and `/api` on one origin. Vite production assets must retain the `/static/` base configured in `frontend/vite.config.js`.
- `FRONTEND_URL` should be `https://ecommerce-api-rysy.onrender.com`. Set `DJANGO_ALLOWED_HOSTS` to `ecommerce-api-rysy.onrender.com` and `MERCADOPAGO_WEBHOOK_URL` to `https://ecommerce-api-rysy.onrender.com/api/orders/payments/webhook/` in Render.
- The fresh production catalog currently has one Smart TV product. Its API currently reports `"image": null`, so the storefront displays its initial. Do not rely on Render's ephemeral filesystem for uploads; next task is integrate a persistent image provider such as Cloudinary before adding product images.
- Mercado Pago generated and redirected to the sandbox checkout, so preference creation works. The sandbox login then failed in Firefox. Retry in an incognito window without VPN using a `TESTUSER...` buyer account. The real account that owns the `TEST-` token is only for application and webhook configuration.
- Payment reservations expire after 30 minutes. `python manage.py expire_payment_reservations` cancels expired online reservations and restores stock; schedule it externally in a non-free production environment. Paid orders cannot be cancelled without a prior refund.
