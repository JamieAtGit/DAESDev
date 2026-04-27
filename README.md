# Bristol Regional Food Network — Digital Marketplace

A Django/DRF marketplace connecting local food producers with consumers within a 20-mile radius of Bristol city centre.

## Requirements

- Docker
- Docker Compose

## Setup and Running

### 1. Clone the repository

```bash
git clone <repo-url>
cd DAESDev
```

### 2. Start the application

```bash
docker-compose up --build
```

This will:
- Start a PostgreSQL 15 database
- Run Django migrations automatically
- Start the web server at [http://localhost:8000](http://localhost:8000)

### 3. Seed test data (optional)

```bash
docker-compose exec -T web python manage.py shell < seed.py
```

Creates three producers, sample customers, a community group, and a restaurant account with products, surplus listings, and community posts pre-populated.

**Seeded test accounts:**

| Username | Password | Role |
|---|---|---|
| `farmer_john` | `pass1234` | Producer (Green Valley Farm, BS10) |
| `hillside_dairy` | `pass1234` | Producer (Hillside Dairy, BS40) |
| `bakehouse_bristol` | `pass1234` | Producer (Bristol Valley Bakehouse, BS5) |
| `customer1` | `pass1234` | Customer |
| `customer2` | `pass1234` | Customer |
| `stmarys_kitchen` | `pass1234` | Community Group |
| `the_plough` | `pass1234` | Restaurant |

### 4. Create an admin account

```bash
docker-compose exec web python manage.py createsuperuser
```

Admin panel: [http://localhost:8000/admin/](http://localhost:8000/admin/)

## User Roles

| Role | Registration URL | Access |
|---|---|---|
| Customer | `/register/` | Browse, cart, checkout, order history, reviews |
| Community Group | `/register/community/` | Same as customer |
| Restaurant | `/register/community/` | Same as customer |
| Producer | `/register/producer/` | Dashboard, product management, orders, settlements, recalls |
| Admin | Django admin panel | Full system access, commission reports |

## Key Features

- **Product marketplace** — browse, search, and filter by category, organic certification, and allergens
- **Food miles** — straight-line distance calculated per product using producer postcode, displayed on product pages and in cart
- **Cart and checkout** — session-based multi-vendor cart with 5% network commission applied at checkout
- **Recurring orders** — customers can opt in to weekly repeat orders at checkout; manage via `/recurring-orders/`
- **Producer dashboard** — add, edit, and delete products with stock, seasonal availability, and low stock threshold management
- **Low stock alerts** — amber dashboard banner warns producers when a product's stock falls to or below their set threshold
- **Order management** — producers view incoming orders and advance status (Pending → Confirmed → Ready → Delivered)
- **Payment settlements** — auto-generated per producer on each order; CSV export at `/settlements/export/`
- **Admin commission report** — staff-only view at `/admin/report/` with date range filtering, period totals, year-to-date commission, and CSV export
- **Surplus produce** — producers list short-dated or excess stock at a discount (10–50% off) via `/surplus/`
- **Community board** — producers share farm stories, recipes, and storage tips linked to their products
- **Recall notices** — producers issue food safety recalls; system identifies all affected customer orders within the date range
- **Product reviews** — customers can leave a verified star rating and review for any product from a delivered order; one review per product per customer
- **REST API** — available at `/api/` (products, categories, orders, surplus, community posts)

## Security

- Passwords hashed using Django's PBKDF2-SHA256 algorithm
- Brute-force protection — 5 failed login attempts from the same IP/username combination triggers a 15-minute lockout
- Audit log — all login, logout, failed login, order, and recall events recorded with timestamp and IP address
- Role-based access control — all producer and admin routes enforce role checks server-side
- Session timeout — sessions expire after 2 hours of inactivity
- CSRF protection enabled on all forms

## Stopping the Application

```bash
docker-compose down
```

To also remove the database volume:

```bash
docker-compose down -v
```
