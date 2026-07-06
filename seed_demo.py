"""
Run this after seed.py to populate orders, reviews, recall notices,
settlements, audit log entries, and an admin account for demo purposes.

    docker-compose exec -T web python manage.py shell < seed_demo.py
"""

from marketplace.models import (
    CustomUser, ProducerProfile, Product,
    Order, OrderItem, PaymentSettlement,
    RecallNotice, Review, AuditLog,
)
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone

today = date.today()

# ── Clear any previous demo orders/reviews/recalls so this is re-runnable ───
Order.objects.all().delete()
RecallNotice.objects.all().delete()
AuditLog.objects.all().delete()

# ── Admin account ────────────────────────────────────────────────────────────
if not CustomUser.objects.filter(username='admin').exists():
    CustomUser.objects.create_superuser(
        username='admin', password='admin1234',
        email='admin@brfn.local', role='admin'
    )
    print("Created admin / admin1234")

# ── Fetch existing users and producers ──────────────────────────────────────
sarah     = CustomUser.objects.get(username='sarah_jones')
robert    = CustomUser.objects.get(username='robert_johnson')
restaurant = CustomUser.objects.get(username='the_clifton_kitchen')
community  = CustomUser.objects.get(username='st_marys_school')

p1 = ProducerProfile.objects.get(business_name="John's Farm")
p2 = ProducerProfile.objects.get(business_name="Hillside Dairy")
p3 = ProducerProfile.objects.get(business_name="Bristol Valley Bakehouse")

# ── Fetch products ───────────────────────────────────────────────────────────
carrots   = Product.objects.get(producer=p1, name="Organic Carrots")
potatoes  = Product.objects.get(producer=p1, name="Organic Potatoes")
leeks     = Product.objects.get(producer=p1, name="Organic Leeks")
eggs      = Product.objects.get(producer=p1, name="Free Range Eggs")
milk      = Product.objects.get(producer=p2, name="Whole Milk (2 litres)")
cheddar   = Product.objects.get(producer=p2, name="Mature Cheddar (250g)")
butter    = Product.objects.get(producer=p2, name="Salted Butter (250g)")
yoghurt   = Product.objects.get(producer=p2, name="Natural Yoghurt (500g)")
honey     = Product.objects.get(producer=p2, name="Chew Valley Honey (340g)")
sourdough = Product.objects.get(producer=p1, name="Sourdough Loaf")
rye       = Product.objects.get(producer=p3, name="Seeded Rye Loaf")
scones    = Product.objects.get(producer=p3, name="Cheese and Herb Scones (4)")

# Set honey to low stock so the dashboard alert fires during demo
honey.stock = 3
honey.low_stock_threshold = 5
honey.save()

# ── Helper ───────────────────────────────────────────────────────────────────
def week_ending(d):
    """Return the Sunday on or after d."""
    return d + timedelta(days=(6 - d.weekday()))

def make_order(customer, items, status, days_ago, delivery_offset=2, instructions=''):
    """
    items: list of (product, qty)
    Returns the saved Order with items and settlements attached.
    """
    gross = sum(p.price * qty for p, qty in items)
    commission = (gross * Decimal('0.05')).quantize(Decimal('0.01'))
    total = gross + commission
    delivery = today - timedelta(days=days_ago - delivery_offset)

    order = Order.objects.create(
        customer=customer,
        total_price=total,
        commission_amount=commission,
        status=status,
        delivery_address=customer.delivery_address or '1 Demo Street, Bristol',
        delivery_date=delivery,
        special_instructions=instructions,
    )

    # backdate created_at
    Order.objects.filter(pk=order.pk).update(
        created_at=timezone.now() - timedelta(days=days_ago)
    )
    order.refresh_from_db()

    for product, qty in items:
        OrderItem.objects.create(
            order=order, product=product,
            quantity=qty, unit_price=product.price
        )

    # settlements grouped by producer
    producer_totals = {}
    for product, qty in items:
        prod = product.producer
        producer_totals[prod] = producer_totals.get(prod, Decimal('0')) + product.price * qty

    for producer, gross_amt in producer_totals.items():
        comm = (gross_amt * Decimal('0.05')).quantize(Decimal('0.01'))
        PaymentSettlement.objects.create(
            producer=producer,
            order=order,
            gross_amount=gross_amt,
            commission_deducted=comm,
            net_amount=gross_amt - comm,
            status='paid' if status == 'delivered' else 'pending',
            week_ending=week_ending(order.created_at.date()),
        )

    AuditLog.objects.create(
        user=customer,
        action=f'Order #{order.id} placed',
        resource_type='Order',
        resource_id=str(order.id),
        ip_address='127.0.0.1',
        notes=f'Total: £{total} | Status: {status}',
    )

    return order


# ── Order 1 — sarah_jones, DELIVERED, 3 weeks ago ────────────────────────────
# Covers TC-009, TC-010, TC-011, TC-012, TC-021, TC-024
o1 = make_order(
    sarah,
    [(carrots, 2), (eggs, 1), (milk, 1)],
    status='delivered',
    days_ago=21,
    instructions='Please leave by the gate if nobody answers.',
)
AuditLog.objects.create(
    user=p1.user, action=f'Order #{o1.id} status changed to Delivered',
    resource_type='Order', resource_id=str(o1.id), ip_address='127.0.0.1',
)

# ── Order 2 — sarah_jones, READY FOR DELIVERY ────────────────────────────────
o2 = make_order(
    sarah,
    [(sourdough, 1), (rye, 1)],
    status='ready',
    days_ago=3,
)
AuditLog.objects.create(
    user=p3.user, action=f'Order #{o2.id} status changed to Ready for Delivery',
    resource_type='Order', resource_id=str(o2.id), ip_address='127.0.0.1',
)

# ── Order 3 — robert_johnson, CONFIRMED ─────────────────────────────────────
o3 = make_order(
    robert,
    [(cheddar, 1), (butter, 1), (potatoes, 2)],
    status='confirmed',
    days_ago=5,
)
AuditLog.objects.create(
    user=p2.user, action=f'Order #{o3.id} status changed to Confirmed',
    resource_type='Order', resource_id=str(o3.id), ip_address='127.0.0.1',
)

# ── Order 4 — robert_johnson, PENDING ───────────────────────────────────────
o4 = make_order(
    robert,
    [(scones, 2)],
    status='pending',
    days_ago=1,
)

# ── Order 5 — the_clifton_kitchen, DELIVERED (restaurant bulk order) ─────────
o5 = make_order(
    restaurant,
    [(milk, 4), (yoghurt, 2), (butter, 2)],
    status='delivered',
    days_ago=14,
)

# ── Order 6 — st_marys_school, CONFIRMED (community group) ──────────────────
o6 = make_order(
    community,
    [(carrots, 3), (leeks, 2), (eggs, 2)],
    status='confirmed',
    days_ago=4,
    instructions='School kitchen delivery — ring the bell at the side entrance.',
)

# ── Order 7 — sarah_jones, older DELIVERED order (for review variety) ────────
o7 = make_order(
    sarah,
    [(cheddar, 1), (honey, 1)],
    status='delivered',
    days_ago=35,
)

# ── Reviews — only on delivered orders ──────────────────────────────────────
# TC-024: verified reviews, one per customer per product

Review.objects.get_or_create(
    customer=sarah, product=carrots,
    defaults=dict(
        order=o1, rating=5,
        title='Best carrots I have bought',
        body='Really sweet and fresh — arrived well packaged. Will definitely order again.',
    )
)

Review.objects.get_or_create(
    customer=sarah, product=eggs,
    defaults=dict(
        order=o1, rating=5,
        title='Proper free range eggs',
        body='Deep orange yolks, noticeably better than supermarket eggs. Great for baking.',
    )
)

Review.objects.get_or_create(
    customer=sarah, product=milk,
    defaults=dict(
        order=o1, rating=4,
        title='Good quality milk',
        body='Fresh and creamy. Arrived cold, good packaging. Slightly pricier than the shop but worth it.',
    )
)

Review.objects.get_or_create(
    customer=sarah, product=cheddar,
    defaults=dict(
        order=o7, rating=5,
        title='Excellent mature cheddar',
        body='Aged well, really sharp flavour. Great on a cheeseboard or in cooking.',
    )
)

Review.objects.get_or_create(
    customer=sarah, product=honey,
    defaults=dict(
        order=o7, rating=5,
        title='Beautiful local honey',
        body='Proper raw honey, not the watery stuff you get in supermarkets. Lovely floral flavour.',
    )
)

Review.objects.get_or_create(
    customer=restaurant, product=milk,
    defaults=dict(
        order=o5, rating=5,
        title='Reliable supply for the kitchen',
        body='We use this for sauces and desserts. Consistent quality and always arrives on time.',
    )
)

Review.objects.get_or_create(
    customer=restaurant, product=yoghurt,
    defaults=dict(
        order=o5, rating=4,
        title='Good live yoghurt',
        body='Clean, slightly tangy flavour. Works well as a base for dressings and marinades.',
    )
)

# ── Recall Notice — TC-018 ───────────────────────────────────────────────────
recall = RecallNotice.objects.create(
    product=eggs,
    issued_by=p1,
    reason='Potential contamination identified during routine inspection of Batch APR-15. '
           'As a precaution, all eggs from this batch are being recalled. '
           'Customers who purchased eggs between 15 and 22 April should not consume them.',
    batch_info='Batch APR-15',
    status='issued',
    affected_from=date(2026, 4, 15),
    affected_to=date(2026, 4, 22),
)
AuditLog.objects.create(
    user=p1.user,
    action=f'Recall notice issued for {eggs.name} (Batch APR-15)',
    resource_type='RecallNotice',
    resource_id=str(recall.id),
    ip_address='127.0.0.1',
)

# ── Additional audit log entries for demo ────────────────────────────────────
AuditLog.objects.create(
    user=None,
    action='Failed login attempt for username: admin',
    resource_type='CustomUser', resource_id='',
    ip_address='192.168.1.50',
)
AuditLog.objects.create(
    user=None,
    action='Failed login attempt for username: admin',
    resource_type='CustomUser', resource_id='',
    ip_address='192.168.1.50',
)
AuditLog.objects.create(
    user=sarah,
    action='User logged in',
    resource_type='CustomUser', resource_id=str(sarah.id),
    ip_address='127.0.0.1',
)

# ── Summary ──────────────────────────────────────────────────────────────────
print("Demo seed complete.")
print("")
print(f"  Orders created:       7  (statuses: delivered x3, ready x1, confirmed x2, pending x1)")
print(f"  Reviews created:      7")
print(f"  Recall notices:       1  (Free Range Eggs, Batch APR-15)")
print(f"  Settlements:          {PaymentSettlement.objects.count()}")
print(f"  Audit log entries:    {AuditLog.objects.count()}")
print(f"  Honey stock:          {honey.stock} (threshold: {honey.low_stock_threshold}) — low stock alert will show")
print("")
print("Accounts:")
print("  admin              / admin1234       (superuser — for TC-025 commission report)")
print("  farmer_john        / pass1234        (producer — John's Farm)")
print("  hillside_dairy     / pass1234        (producer — Hillside Dairy)")
print("  valley_bakehouse   / pass1234        (producer — Bristol Valley Bakehouse)")
print("  sarah_jones        / pass1234        (customer — 5 orders, delivered/ready/pending)")
print("  robert_johnson     / pass1234        (customer — 2 orders, confirmed/pending)")
print("  the_clifton_kitchen / pass1234       (restaurant — 1 delivered order)")
print("  st_marys_school    / pass1234        (community group — 1 confirmed order)")
print("")
print("TC-022 demo — brute force lockout:")
print("  Log out, then enter wrong password 5x for any account.")
print("  On the 5th attempt you will be locked out for 15 minutes.")
print("  Session timeout is set to 2 hours of inactivity.")
