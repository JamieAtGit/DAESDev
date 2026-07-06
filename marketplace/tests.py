# tests.py — checks the simulated card payment at checkout.
# Run with: python manage.py test marketplace

from datetime import date, timedelta

from django.test import TestCase

from .models import (
    Category, CustomUser, Order, PaymentSettlement, PaymentTransaction,
    ProducerProfile, Product,
)


class CheckoutPaymentTests(TestCase):
    def setUp(self):
        producer_user = CustomUser.objects.create_user(
            username='farmer', password='pass1234', role='producer'
        )
        self.producer = ProducerProfile.objects.create(
            user=producer_user, business_name='Test Farm', address='1 Lane', postcode='BS10 5AA'
        )
        category = Category.objects.create(name='Vegetables', slug='vegetables')
        self.product = Product.objects.create(
            producer=self.producer, category=category, name='Carrots',
            description='Fresh', price='2.50', stock=20,
        )
        CustomUser.objects.create_user(
            username='cust', password='pass1234', role='customer',
            delivery_address='2 Road', delivery_postcode='BS1 1AA',
        )
        self.client.login(username='cust', password='pass1234')
        # Put 4 x carrots (£10.00) in the session cart
        session = self.client.session
        session['cart'] = {
            str(self.product.id): {
                'name': 'Carrots', 'price': '2.50', 'quantity': 4,
                'producer': 'Test Farm', 'producer_postcode': 'BS10 5AA',
            }
        }
        session.save()

    def test_card_payment_places_order(self):
        response = self.client.post('/checkout/', {
            'full_name': 'Test Customer',
            'email': 'cust@test.com',
            'postcode': 'BS1 1AA',
            'delivery_address': '2 Road',
            'delivery_date': (date.today() + timedelta(days=3)).isoformat(),
            'card_number': '4242 4242 4242 4242',
            'card_expiry': '08/28',
            'card_cvv': '123',
        })
        self.assertRedirects(response, '/')
        # £10.00 subtotal + 5% commission = £10.50
        order = Order.objects.get()
        self.assertEqual(str(order.total_price), '10.50')
        self.assertEqual(str(order.commission_amount), '0.50')
        # The payment was recorded with a gateway reference
        payment = PaymentTransaction.objects.get(order=order)
        self.assertEqual(payment.card_last4, '4242')
        self.assertTrue(payment.transaction_ref.startswith('PAY-'))
        # The producer's settlement keeps 95% of their £10.00 gross
        settlement = PaymentSettlement.objects.get(order=order)
        self.assertEqual(str(settlement.net_amount), '9.50')
        # Stock reduced from 20 to 16
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 16)

    def test_declined_card_does_not_place_order(self):
        response = self.client.post('/checkout/', {
            'full_name': 'Test Customer',
            'email': 'cust@test.com',
            'postcode': 'BS1 1AA',
            'delivery_address': '2 Road',
            'delivery_date': (date.today() + timedelta(days=3)).isoformat(),
            'card_number': '4000 0000 0000 0002',
            'card_expiry': '08/28',
            'card_cvv': '123',
        })
        # The checkout page is shown again with an error message
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(PaymentTransaction.objects.count(), 0)
        # The cart is kept so the customer can retry with another card
        self.assertIn('cart', self.client.session)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 20)
