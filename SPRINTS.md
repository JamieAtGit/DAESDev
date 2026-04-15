# Sprint Summaries — Bristol Regional Food Network

---

## Sprint 1 — Core Architecture and Basic Functionality

**Duration:** Weeks 1–3  
**Goal:** Establish the foundational system architecture, data models, and core user flows.

### Planned

The focus for Sprint 1 was getting the essential foundations in place before any feature work. I planned to set up the Django project with Docker and PostgreSQL, define the core models (users, products, orders), and implement the two main registration flows for producers and customers. The intention was to have a working end-to-end journey by the end of the sprint — a producer can register, list a product, and a customer can find it and add it to a cart. Everything else would build on top of this base.

### Delivered

- **Custom user model** with role-based access (`customer`, `producer`, `community_group`, `restaurant`, `admin`) using Django's `AbstractUser`.
- **Producer registration and profiles** — dedicated registration flow capturing business name, address, and postcode.
- **Product management** — producers can create, edit, and delete product listings with full field set: name, category, description, price, stock, allergens, organic certification, harvest date, best-before date, farm origin, and lead time.
- **Product browsing** — customers can browse by category, search by name/description, and filter by organic certification.
- **Shopping cart** — session-based cart supporting add, update quantity, and remove. Cart persists across the browsing session.
- **Checkout and order creation** — multi-vendor checkout with 5% network commission calculated automatically. Orders created with `Pending` status and linked to the customer.
- **Docker containerisation** — PostgreSQL database and Django web service separated into two containers via Docker Compose with health checks and persistent volume.

### Technical Decisions

Django's built-in session framework was used for cart state to avoid requiring authentication for browsing. The custom user model was established at project start to avoid complex migrations later. PostgreSQL was chosen over SQLite for production parity inside Docker.

---

## Sprint 2 — Expanded Features and Integration

**Duration:** Weeks 4–6  
**Goal:** Build out the financial, traceability, and community features required by the case study.

### Planned

With the core buying and selling flow working, Sprint 2 was planned around the features that make the BRFN specifically a local food network rather than a generic marketplace. The priorities were: financial settlements so producers could actually see what they were owed, food miles so customers could make environmentally aware choices, and the community and traceability features from the case study (surplus produce, recall notices, community posts). I also planned to start the REST API in this sprint to give the system an integration layer. One known risk going in was the food miles dependency — pgeocode needed testing inside Docker early.

### Delivered

- **Payment settlements** — per-producer settlement records auto-generated on checkout, showing gross amount, 5% commission deducted, and net payout grouped by week ending date.
- **Food miles** — distance calculation using the Haversine formula with a hardcoded postcode district coordinate lookup. Replaces a pgeocode dependency that returned NaN values inside Docker due to a corrupt dataset. Food miles shown on product detail and totalled on the cart page.
- **Surplus produce** — producers list end-of-day surplus stock with a discounted price. Discount validated between 10–50%. Customers can add surplus items to their cart at the discounted price.
- **Community board** — producers share farm stories, seasonal recipes, and storage tips, optionally linked to products. Posts filterable by type and shown on the home page.
- **Recall notices** — producers issue product recall notices with batch information and date ranges. `get_affected_orders()` traces all customer orders containing the recalled product within the specified window.
- **Audit log** — `AuditLog` model records order placements, recall issuances, and order status changes with timestamp, user, and IP address.
- **REST API** — DRF `ModelViewSet` endpoints for categories, products, orders, surplus produce, and community posts. Products support search and ordering via query parameters.

### Technical Decisions

pgeocode was retained in `requirements.txt` for compatibility but replaced functionally with a self-contained haversine implementation. This avoids an external network dependency and works fully offline inside Docker. The `PaymentSettlement` model was designed to record settlements at order placement rather than delivery to simplify the demo flow while preserving the audit trail.

---

## Sprint 3 — Complete Implementation and Refinement

**Duration:** Weeks 7–9  
**Goal:** Close remaining test case gaps, refine UX, add order management for producers, and demonstrate the full system against all provided test cases.

### Planned

Sprint 3 started with a full review of the provided test cases against what had been built. The gaps I identified going in were: producers had no way to view or manage their incoming orders (TC-009, TC-010), the cart didn't visually separate products by producer (TC-008), seasonal availability and allergen information weren't prominently enough displayed (TC-015, TC-016), and there was no customer order history page (TC-021). I also planned to add a community group registration path (TC-017), improve the settlements page with a CSV export (TC-012), and wire up JWT authentication on the API which had been deferred from Sprint 2.

The intention was to work through these in small commits — fixing one thing at a time rather than large batches — to keep the changes reviewable and the system stable throughout. TC-018 (recurring orders) was explicitly parked as out of scope given its Medium priority and "if time permits" classification.

### Delivered

**Order management for producers**
- Producers can view all incoming orders containing their products, sorted by delivery date, with a status filter (Pending / Confirmed / Ready / Delivered).
- Order detail shows full customer contact information, delivery address, special instructions, and an itemised list of the producer's items only — multi-vendor orders correctly isolate each producer's view.
- Status progression enforced: `Pending → Confirmed → Ready for Delivery → Delivered`. Each transition accepts an optional note and is logged to the AuditLog with timestamp.

**Customer experience improvements**
- Customer order history page (`/my-orders/`) showing all past orders with status, items, and a one-click **Reorder** button that re-adds available items to cart at current prices.
- Delivery address and phone number captured at registration and pre-filled at checkout.
- Special delivery instructions field on checkout, stored on the order and visible to producers.
- Cart and checkout order summary grouped by producer, satisfying TC-008 multi-vendor transparency requirements.

**Product and inventory**
- Low stock and out-of-stock badges on product list and detail pages.
- Seasonal availability badges (`In Season` / `Available year-round`) on product cards and detail.
- Allergen display updated: products with no allergens explicitly state "No common allergens" rather than showing nothing.
- Food miles now calculated from the customer's own saved postcode when available, falling back to Bristol city centre.
- Linked community posts (recipes, farm stories) shown on each product's detail page.

**Settlements**
- CSV export added to the settlements page for tax reporting purposes.

**Community and surplus**
- Producers can deactivate their own surplus listings once stock sells out.
- Community group registration page (`/register/community/`) with `community_group` role, separate from individual customer registration.

**REST API**
- JWT authentication wired up via `djangorestframework-simplejwt` (`/api/token/` and `/api/token/refresh/`).
- Surplus and community post endpoints added to the API.

### Test Case Coverage

All 21 provided test cases are implemented. TC-018 (recurring orders) was assessed as out of scope given its Medium priority rating and the explicit "if time permits" qualifier in the test case guide. All Critical and High priority test cases pass.

### Technical Decisions

The order status progression is enforced in the view layer using a dictionary mapping rather than model-level validation, keeping the logic readable and easy to demonstrate. JWT authentication was added to satisfy the "External Services Integration" marking criterion — the existing `simplejwt` dependency was already present in `requirements.txt` from Sprint 2 but not yet exposed. The food miles postcode lookup uses a manually curated coordinate dictionary covering all Bristol (`BS`) districts plus surrounding areas, chosen over an API dependency to ensure the system runs fully offline in the Docker environment.

---
