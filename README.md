# Django E-Commerce Store

A complete, portfolio-ready online store built with **Python and Django**: catalogue with search, filters, sorting and pagination; session-based shopping cart; registration and login; transactional checkout; order history and tracking; a staff dashboard; and a configured Django admin. It works fully offline after installation (no CDN, no external images).

## Features

**Customers**
- Home page with hero, category cards, Featured and Latest products (all from the database)
- Shop page: name search (partial match), category filter, min/max price filter, 5 sort orders, pagination
- Product pages with discount badge and dynamic discount %, stock status, quantity selector and related products
- Cart: add, remove, increase, decrease, set quantity, stock validation ("Only 3 items are available."), subtotal / shipping / total
- Register, log in (username **or** email), log out, profile with saved contact details
- Checkout (Cash on Delivery / demo checkout), order confirmation (`ORD-00001` numbers), order history, order detail with status timeline

**Administrators**
- Django admin for products (thumbnail, inline stock and featured editing, stock filter, search), categories, users, orders (status filter/search, bulk status actions, read-only line items)
- `/dashboard/` (staff only): total products, orders, customers, revenue, recent orders, low-stock products, best sellers, order-status summary. Every figure is a database query.

**Engineering**
- Order creation in one `transaction.atomic` block with atomic conditional stock decrement (no overselling, no partial orders)
- `OrderItem` stores product name and price snapshots, so history stays correct if products change or are deleted
- Users can only open their own orders (others get 404); dashboard is staff-only; POST-only cart/logout actions; CSRF everywhere
- Uploaded product images are validated (extension, size, real image content, format)
- Database constraints (discount < price, quantity >= 1), indexes, `select_related` to avoid N+1 queries
- 84 automated tests

## Technology stack
Python 3.10+, Django 5.1+ (developed on 6.x), SQLite, Pillow, hand-written HTML5 / CSS3 / vanilla JavaScript (no frameworks).

## Screenshots
Screenshots were not captured in the build environment (no modern headless browser was available). After running the site, add your own to `docs/screenshots/` and link them here.

## Project structure
```
ecommerce_project/
├── manage.py
├── ecommerce_project/        settings, urls, wsgi, asgi
├── store/
│   ├── models.py             Category, Product, Order, OrderItem, Profile
│   ├── views.py  urls.py  forms.py  admin.py  tests.py
│   ├── cart.py               session cart + shipping rule
│   ├── services.py           transactional order creation
│   ├── backends.py           username-or-email login
│   ├── validators.py         image upload validation
│   ├── demo_images.py        offline product-image generator
│   ├── management/commands/seed_store.py
│   ├── templates/store/      base, pages, includes/
│   └── static/store/         css/style.css, js/app.js, img/placeholder.svg
├── media/products/           product images (included)
├── requirements.txt  .env.example  .gitignore  README.md
```

## Installation
Windows:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_store
python manage.py runserver
```
Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_store
python manage.py runserver
```
- Store: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- Staff dashboard: http://127.0.0.1:8000/dashboard/ (log in as the superuser)

### Environment variables (optional)
Copy `.env.example` to `.env`. Supported: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `LOW_STOCK_THRESHOLD` (default 5), `SHIPPING_FLAT_RATE` (10.00), `FREE_SHIPPING_THRESHOLD` (500.00, `0` disables), `USE_HTTPS`. With `DEBUG=False` a `SECRET_KEY` is required.

### Database, media and demo data
SQLite (`db.sqlite3`) is created by `migrate`. Product images live in `media/products/` (`MEDIA_URL`/`MEDIA_ROOT`, served by Django in development). `python manage.py seed_store` creates 5 categories and 36 products; it is safe to re-run, and `--reset` wipes products and categories first. It is never run automatically.

### Product images and rights
Internet image sources were not reachable when the project was built, so every demo product has its **own illustration drawn locally with Pillow** (`store/demo_images.py`). They are original artwork with no third-party rights. Files are stored as ordinary `ImageField` uploads in `media/products/`. To use real photos, upload them per product in the admin; source and licence-check them yourself (e.g. Unsplash, Pexels).

## Design decisions
- **Cart**: session-based for everyone. Only product IDs and quantities are stored; prices are read from the database on every request. Checkout requires login, and the cart survives logging in.
- **Shipping**: flat $10.00, free when subtotal >= $500 (both configurable). Empty carts have no shipping.
- **Payment**: Cash on Delivery / demo checkout, clearly labelled. `services.create_order` is the single place to extend when adding a payment gateway.
- **Logout** is a POST (Django's default), so it can't be triggered by a link.

## Testing
```bash
python manage.py check
python manage.py test
```

## How to use
Browse or search, add products to the cart, register or log in, check out, then track the order under **My orders**. As staff, change order status in the admin (**Orders**, then the status column or bulk actions) and watch the customer's timeline update.

## Troubleshooting
- *No products / images:* run `python manage.py seed_store`.
- *Images 404 in production:* Django only serves media when `DEBUG=True`; serve `media/` with your web server.
- *`ModuleNotFoundError: PIL`:* `pip install -r requirements.txt` inside the activated virtualenv.
- *Can't reach the dashboard:* log in with a staff account (the superuser).

## Future improvements
Payment gateway, restoring stock on cancellation, password reset by email, product reviews (only once genuinely implemented), wishlist, order emails, PostgreSQL, Docker.

## Deployment
Set `DEBUG=False`, a strong `SECRET_KEY`, `ALLOWED_HOSTS` and `USE_HTTPS=True`; run `python manage.py collectstatic`; use PostgreSQL; serve with Gunicorn/uWSGI behind Nginx, which also serves `/static/` and `/media/`.
