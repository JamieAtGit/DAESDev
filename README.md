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
- Start the web server on [http://localhost:8000](http://localhost:8000)

### 3. Seed test data (optional)

```bash
docker-compose exec -T web python manage.py shell < seed.py
```

This creates a sample producer (`farmer_john` / `pass1234`) with three products across vegetable, dairy, and bakery categories.

### 4. Create an admin account

```bash
docker-compose exec web python manage.py createsuperuser
```

Admin panel available at [http://localhost:8000/admin/](http://localhost:8000/admin/)

## User Roles

| Role | Registration | Access |
|---|---|---|
| Customer | `/register/` | Browse, cart, checkout, order history |
| Producer | `/register/producer/` | Dashboard, product management, orders, settlements |
| Admin | Django admin panel | Full system access |

## Key Features

- **Product marketplace** — browse, search, filter by category and organic certification
- **Food miles** — distance from Bristol centre calculated per product using producer postcode
- **Cart and checkout** — multi-vendor orders with 5% network commission
- **Producer dashboard** — add, edit, delete products with stock and seasonal management
- **Order management** — producers view incoming orders and update status (Pending → Confirmed → Ready → Delivered)
- **Payment settlements** — auto-generated per producer on checkout, CSV export available
- **Surplus produce** — producers list end-of-day discounted stock
- **Community board** — producers share farm stories, recipes, and storage tips
- **Recall notices** — producers issue product recalls linked to affected customer orders
- **REST API** — available at `/api/` (products, categories, orders)

## Stopping the Application

```bash
docker-compose down
```

To also remove the database volume:

```bash
docker-compose down -v
```
