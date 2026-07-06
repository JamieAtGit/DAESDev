# payments.py — fake payment gateway used at checkout.
# The brief says real payment systems must not be used, so this simulates one:
# any 16-digit card number is "charged" successfully, except the decline card
# below which always fails (same idea as Stripe's test cards).

import uuid

DECLINE_CARD = '4000000000000002'


def process_card_payment(card_number, amount):
    # Returns (True, reference) on success or (False, error message) on failure
    number = card_number.replace(' ', '')
    if number == DECLINE_CARD:
        return False, 'Card was declined.'
    return True, 'PAY-' + uuid.uuid4().hex[:12].upper()
