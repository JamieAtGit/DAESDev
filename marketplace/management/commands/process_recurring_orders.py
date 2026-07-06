from datetime import date, timedelta

from django.core.management.base import BaseCommand

from marketplace.models import (
    AuditLog, Order, OrderItem, PaymentSettlement,
    RecurringOrder, RecurringOrderItem,
)


class Command(BaseCommand):
    help = (
        'Generate new orders from active recurring order templates whose next_order_date '
        'is today or in the past. Run daily via cron or: '
        'docker-compose exec web python manage.py process_recurring_orders'
    )

    def handle(self, *args, **options):
        today = date.today()
        due = RecurringOrder.objects.filter(
            is_active=True,
            next_order_date__lte=today,
        ).select_related('customer').prefetch_related('items__product__producer')

        created = 0
        for rec in due:
            items = [i for i in rec.items.all() if i.product and i.product.is_active]
            if not items:
                self.stdout.write(
                    self.style.WARNING(f'Skipping recurring order #{rec.id} — no active items')
                )
                continue

            subtotal = sum(float(i.unit_price) * i.quantity for i in items)
            commission = round(subtotal * 0.05, 2)
            grand_total = round(subtotal + commission, 2)

            # Derive delivery date: find next occurrence of delivery_day after order date
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2,
                'thursday': 3, 'friday': 4, 'saturday': 5,
            }
            order_day_num = day_map.get(rec.recurrence_day, 0)
            delivery_day_num = day_map.get(rec.delivery_day, 2)
            days_ahead = (delivery_day_num - order_day_num) % 7 or 7
            delivery_date = rec.next_order_date + timedelta(days=days_ahead)

            order = Order.objects.create(
                customer=rec.customer,
                delivery_address=rec.delivery_address,
                delivery_date=delivery_date,
                special_instructions=rec.special_instructions,
                total_price=grand_total,
                commission_amount=commission,
            )

            producers_in_order = set()
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                item.product.stock = max(0, item.product.stock - item.quantity)
                item.product.save(update_fields=['stock'])
                producers_in_order.add(item.product.producer)

            # Per-producer settlement (same logic as checkout view)
            week_ending = today + timedelta(days=(6 - today.weekday()))
            for producer in producers_in_order:
                producer_items = order.items.filter(product__producer=producer)
                gross = sum(float(i.unit_price) * i.quantity for i in producer_items)
                producer_commission = round(gross * 0.05, 2)
                net = round(gross - producer_commission, 2)
                PaymentSettlement.objects.create(
                    producer=producer,
                    order=order,
                    gross_amount=gross,
                    commission_deducted=producer_commission,
                    net_amount=net,
                    week_ending=week_ending,
                )

            AuditLog.objects.create(
                user=rec.customer,
                action=f'Order #{order.id} auto-generated from recurring order #{rec.id}',
                resource_type='Order',
                resource_id=str(order.id),
            )

            # Advance template to next week
            rec.next_order_date = rec.next_order_date + timedelta(weeks=1)
            rec.save(update_fields=['next_order_date'])

            self.stdout.write(
                self.style.SUCCESS(
                    f'Created Order #{order.id} for {rec.customer.username} '
                    f'(recurring #{rec.id}, delivery {delivery_date})'
                )
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Done — {created} order(s) generated.'))
