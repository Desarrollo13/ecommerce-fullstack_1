# E-commerce Backend

## Run And Verify

- Run Django commands from `backend/` with the repository's sibling virtual environment: `..\venv\Scripts\python.exe manage.py <command>`.
- Use `..\venv\Scripts\python.exe manage.py check` for a fast configuration check.
- Before committing model changes, run `..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run`; create migrations with `..\venv\Scripts\python.exe manage.py makemigrations <app>` and apply them with `..\venv\Scripts\python.exe manage.py migrate`.
- Run the current app test target with `..\venv\Scripts\python.exe manage.py test users cart orders products`. Tests and database-backed commands require the local MySQL instance configured in `config/settings.py` (`ecommerce_db` on `localhost:3306`).
- Dependencies are installed only in the sibling `venv/`; this repository has no requirements or lockfile.

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
