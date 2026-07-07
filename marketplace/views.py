# views.py — request handling for every page in the marketplace.
# Each function maps to a URL in urls.py and returns an HTTP response.
# Role checks at the top of each view enforce access control.

import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Avg, F
from .forms import RegisterForm, ProducerRegistrationForm, CommunityGroupRegistrationForm, ProductForm, CheckoutForm, CommunityPostForm, RecallNoticeForm, ReviewForm
from .models import ProducerProfile, Product, Category, Order, OrderItem, SurplusProduce, CommunityPost, PaymentSettlement, PaymentTransaction, ProducerDeliveryDate, AuditLog, RecallNotice, RecurringOrder, RecurringOrderItem, Review
from .surplus_forms import SurplusProduceForm
from .food_miles import calculate_food_miles
from .payments import process_card_payment
from django.utils import timezone
from django.shortcuts import get_object_or_404


# ── Homepage ─────────────────────────────────────────────────────────────────

def home(request):
    # Pull a small selection of recent products, surplus deals, and community posts for the landing page
    recent_products = Product.objects.filter(is_active=True).select_related('producer', 'category').order_by('-created_at')[:6]
    surplus = SurplusProduce.objects.filter(
        is_active=True, available_until__gte=timezone.now()
    ).select_related('product', 'product__producer').order_by('available_until')[:3]
    community_posts = CommunityPost.objects.select_related('producer').order_by('-created_at')[:3]
    return render(request, 'marketplace/home.html', {
        'recent_products': recent_products,
        'surplus': surplus,
        'community_posts': community_posts,
    })


# ── Authentication ───────────────────────────────────────────────────────────

def register(request):  # TC-002: customer registration
    # Redirect logged-in users away — they don't need to register again
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created! Please log in.')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'marketplace/register.html', {'form': form})


def login_view(request):  # TC-022: brute-force protection, session management, audit logging
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        username = request.POST.get('username', '')[:50]
        # Keying on both IP and username means a lockout on one account doesn't
        # block other users logging in from the same network
        cache_key = f'login_attempts_{ip}_{username}'
        attempts = cache.get(cache_key, 0)
        if attempts >= 5:
            # 5 failed attempts triggers a 15-minute block (timeout=900 seconds below)
            messages.error(request, 'Too many failed login attempts. Please try again in 15 minutes.')
            return render(request, 'marketplace/login.html', {'form': AuthenticationForm()})
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Clear the counter on successful login so a later mistake doesn't trigger a lockout
            cache.delete(cache_key)
            AuditLog.objects.create(
                user=user,
                action='User logged in',
                resource_type='CustomUser',
                resource_id=str(user.id),
                ip_address=ip,
            )
            return redirect('home')
        else:
            # Increment and store the counter; timeout=900 means it auto-expires after 15 minutes
            cache.set(cache_key, attempts + 1, timeout=900)
            AuditLog.objects.create(
                user=None,
                action=f'Failed login attempt for username: {username}',
                resource_type='CustomUser',
                resource_id='',
                ip_address=ip,
            )
    else:
        form = AuthenticationForm()
    return render(request, 'marketplace/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.objects.create(
            user=request.user,
            action='User logged out',
            resource_type='CustomUser',
            resource_id=str(request.user.id),
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    logout(request)
    return redirect('home')


def register_community_group(request):  # TC-017: community group and restaurant registration
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = CommunityGroupRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'community_group'
            user.first_name = form.cleaned_data.get('organisation_name', '')
            user.phone = form.cleaned_data.get('phone', '')
            user.delivery_address = form.cleaned_data.get('delivery_address', '')
            user.delivery_postcode = form.cleaned_data.get('delivery_postcode', '')
            user.save()
            messages.success(request, 'Community group account created! Please log in.')
            return redirect('login')
    else:
        form = CommunityGroupRegistrationForm()
    return render(request, 'marketplace/community_group_register.html', {'form': form})


def register_producer(request):  # TC-001: producer registration, creates linked ProducerProfile
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = ProducerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'producer'
            user.phone = form.cleaned_data.get('phone', '')
            user.save()
            # Create the linked ProducerProfile with the business details from the form
            ProducerProfile.objects.create(
                user=user,
                business_name=form.cleaned_data['business_name'],
                address=form.cleaned_data['address'],
                postcode=form.cleaned_data['postcode'],
                description=form.cleaned_data.get('description', ''),
            )
            messages.success(request, 'Producer account created! Please log in.')
            return redirect('login')
    else:
        form = ProducerRegistrationForm()
    return render(request, 'marketplace/producer_register.html', {'form': form})


# ── Producer dashboard & product management ──────────────────────────────────

@login_required
def dashboard(request):  # TC-023: low stock alerts; TC-003: product management entry point
    if request.user.role != 'producer':
        return redirect('home')
    profile, _ = ProducerProfile.objects.get_or_create(user=request.user)
    products = Product.objects.filter(producer=profile).order_by('-created_at')
    # Surface any products whose stock has fallen to or below the producer's set threshold
    low_stock_products = products.filter(low_stock_threshold__gt=0, stock__lte=F('low_stock_threshold'))
    return render(request, 'marketplace/dashboard.html', {
        'products': products,
        'profile': profile,
        'low_stock_products': low_stock_products,
    })


@login_required
def product_create(request):  # TC-003: create a new product listing
    if request.user.role != 'producer':
        return redirect('home')
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            # Attach the product to the currently logged-in producer before saving
            product.producer = request.user.producer_profile
            product.save()
            messages.success(request, f'Product "{product.name}" created.')
            return redirect('dashboard')
    else:
        form = ProductForm()
    return render(request, 'marketplace/product_form.html', {'form': form, 'action': 'Create'})


@login_required
def product_edit(request, pk):  # TC-011: update stock and availability; TC-016: seasonal settings
    if request.user.role != 'producer':
        return redirect('home')
    # The producer check in the query prevents one producer editing another's product via a guessed URL
    product = Product.objects.get(pk=pk, producer=request.user.producer_profile)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated.')
            return redirect('dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'marketplace/product_form.html', {'form': form, 'action': 'Edit', 'product': product})


@login_required
def product_delete(request, pk):
    if request.user.role != 'producer':
        return redirect('home')
    product = Product.objects.get(pk=pk, producer=request.user.producer_profile)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
        return redirect('dashboard')
    return render(request, 'marketplace/product_confirm_delete.html', {'product': product})


# ── Product browsing ─────────────────────────────────────────────────────────

def product_list(request):  # TC-004: category browse; TC-005: search; TC-014: organic filter; TC-015: allergen filter; TC-016: seasonal; TC-023: out-of-stock hiding
    # Exclude inactive and out-of-stock products (TC-023 acceptance criterion)
    products = Product.objects.filter(is_active=True, stock__gt=0).select_related('producer', 'category')
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    organic = request.GET.get('organic', '')
    allergen = request.GET.get('allergen', '')

    if search:
        # The | operator produces an OR query — matches name or description, case-insensitive
        products = products.filter(name__icontains=search) | products.filter(description__icontains=search)
    if category:
        products = products.filter(category__slug=category)
    if organic:
        products = products.filter(is_organic=True)
    if allergen == 'none':
        # 'none' means the customer wants products with no allergens listed at all
        products = products.filter(allergens='') | products.filter(allergens__iexact='none')
    elif allergen:
        products = products.filter(allergens__icontains=allergen)

    # TC-016: hide out-of-season products — only applies when season months are explicitly set
    from datetime import date as _date
    current_month = _date.today().month
    visible = []
    for p in products:
        if p.is_seasonal and p.season_start_month and p.season_end_month:
            start, end = p.season_start_month, p.season_end_month
            if start <= end:
                in_season = start <= current_month <= end
            else:  # season spans year boundary (e.g. Oct–Feb)
                in_season = current_month >= start or current_month <= end
            if not in_season:
                continue
        visible.append(p)

    return render(request, 'marketplace/product_list.html', {
        'products': visible,
        'categories': Category.objects.all(),
        'search': search,
        'category': category,
        'organic': organic,
        'allergen': allergen,
    })


def product_detail(request, pk):  # TC-013: food miles; TC-015: allergens; TC-024: reviews display
    product = get_object_or_404(Product, pk=pk, is_active=True)
    food_miles = None
    if product.producer.postcode:
        # Use the customer's saved postcode if available; BS1 1AA (city centre) is the fallback
        # so food miles are always shown even for anonymous visitors
        customer_postcode = (
            request.user.delivery_postcode
            if request.user.is_authenticated and request.user.delivery_postcode
            else 'BS11AA'
        )
        food_miles = calculate_food_miles(customer_postcode, product.producer.postcode)
    linked_posts = product.community_posts.select_related('producer').order_by('-created_at')[:3]
    reviews = product.reviews.select_related('customer').order_by('-created_at')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    user_review = reviews.filter(customer=request.user).first() if request.user.is_authenticated else None
    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'food_miles': food_miles,
        'linked_posts': linked_posts,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1) if avg_rating else None,
        'user_review': user_review,
    })


# ── Cart (stored in the session, not the database) ───────────────────────────

@login_required
def cart_add(request, pk):  # TC-006: add item to session cart
    if request.method != 'POST':
        return redirect('product_list')
    product = get_object_or_404(Product, pk=pk, is_active=True)
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    product_id = str(pk)
    if product_id in cart:
        # Product already in cart — just increase the quantity
        cart[product_id]['quantity'] += quantity
    else:
        cart[product_id] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': quantity,
            'producer': product.producer.business_name,
            'producer_postcode': product.producer.postcode,
        }
    request.session['cart'] = cart
    messages.success(request, f'"{product.name}" added to cart.')
    return redirect('cart_view')


@login_required
def cart_view(request):  # TC-006: view cart; TC-008: grouped by producer; TC-013: food miles total
    cart = request.session.get('cart', {})
    for item in cart.values():
        item['subtotal'] = round(float(item['price']) * item['quantity'], 2)
        postcode = item.get('producer_postcode', '')
        if postcode:
            # Cart doesn't have the customer's postcode easily available, so Bristol centre is used here
            fm = calculate_food_miles('BS11AA', postcode)
            item['food_miles'] = fm
        else:
            item['food_miles'] = None
    total = round(sum(item['subtotal'] for item in cart.values()), 2)
    # Sum food miles only for items where a distance could be calculated
    food_miles_values = [item['food_miles'] for item in cart.values() if item['food_miles'] is not None]
    total_food_miles = round(sum(food_miles_values), 1) if food_miles_values else None
    return render(request, 'marketplace/cart.html', {
        'cart': cart,
        'total': total,
        'total_food_miles': total_food_miles,
    })


@login_required
def cart_remove(request, pk):
    if request.method != 'POST':
        return redirect('cart_view')
    cart = request.session.get('cart', {})
    cart.pop(str(pk), None)
    request.session['cart'] = cart
    return redirect('cart_view')


# ── Checkout ─────────────────────────────────────────────────────────────────

@login_required
def checkout(request):  # TC-007: single producer order; TC-008: multi-vendor; TC-018: recurring order setup; TC-025: commission
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('cart_view')

    for item in cart.values():
        item['subtotal'] = round(float(item['price']) * item['quantity'], 2)

    total = round(sum(item['subtotal'] for item in cart.values()), 2)
    commission = round(total * 0.05, 2)   # platform takes 5% of every order
    grand_total = round(total + commission, 2)

    # Each producer in the cart gets their own delivery date field on the form
    producer_names = sorted({item['producer'] for item in cart.values()})

    if request.method == 'POST':
        form = CheckoutForm(request.POST, producers=producer_names)
        if form.is_valid():
            # "Charge" the card first — no order is created if the payment fails
            payment_ok, payment_ref = process_card_payment(
                form.cleaned_data['card_number'], grand_total
            )
            if not payment_ok:
                # Log the failed attempt so declined payments are traceable
                AuditLog.objects.create(
                    user=request.user,
                    action='Payment declined at checkout',
                    resource_type='Payment',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    notes=payment_ref,
                )
                messages.error(request, f'Payment failed: {payment_ref} Your order has not been placed.')
                return render(request, 'marketplace/checkout.html', {
                    'form': form,
                    'cart': cart,
                    'total': total,
                    'commission': commission,
                    'grand_total': grand_total,
                })
            # Save the order record — its delivery_date is the earliest of the
            # per-producer dates chosen on the form
            delivery_dates = form.delivery_dates()
            order = Order.objects.create(
                customer=request.user,
                delivery_address=form.cleaned_data['delivery_address'],
                delivery_date=min(delivery_dates.values()),
                special_instructions=form.cleaned_data.get('special_instructions', ''),
                total_price=grand_total,
                commission_amount=commission,
            )
            # Create an OrderItem for each product and reduce stock accordingly
            for product_id, item in cart.items():
                product = get_object_or_404(Product, pk=int(product_id))
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    unit_price=item['price'],
                )
                # max(0, ...) guards against stock going negative if two orders race
                product.stock = max(0, product.stock - item['quantity'])
                product.save(update_fields=['stock'])
            del request.session['cart']

            # Record the payment against the order so it is traceable later
            PaymentTransaction.objects.create(
                order=order,
                amount=grand_total,
                transaction_ref=payment_ref,
                card_last4=form.cleaned_data['card_number'][-4:],
            )

            # Create a PaymentSettlement for each producer involved in this order
            from datetime import date, timedelta
            week_ending = date.today() + timedelta(days=(6 - date.today().weekday()))
            # Build a set of unique producers so multi-vendor orders produce one settlement each
            producers_in_order = set()
            for item in order.items.all():
                if item.product:
                    producers_in_order.add(item.product.producer)
            for producer in producers_in_order:
                # Record the delivery date agreed with this producer
                ProducerDeliveryDate.objects.create(
                    order=order,
                    producer=producer,
                    delivery_date=delivery_dates[producer.business_name],
                )
                # Filter to only this producer's items so the commission split is per-supplier
                producer_items = order.items.filter(product__producer=producer)
                gross = sum(float(i.unit_price) * i.quantity for i in producer_items)
                producer_commission = round(gross * 0.05, 2)  # platform retains 5%
                net = round(gross - producer_commission, 2)   # producer receives the remaining 95%
                PaymentSettlement.objects.create(
                    producer=producer,
                    order=order,
                    gross_amount=gross,
                    commission_deducted=producer_commission,
                    net_amount=net,
                    week_ending=week_ending,
                )

            # Write an audit log entry so admins can trace when this order was placed
            AuditLog.objects.create(
                user=request.user,
                action=f'Order #{order.id} placed',
                resource_type='Order',
                resource_id=str(order.id),
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            # If the customer opted in, save a recurring order template based on this order
            if form.cleaned_data.get('make_recurring'):
                day_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5}
                rec_day = day_map[form.cleaned_data['recurrence_day']]
                today = date.today()
                # Find the next occurrence of the chosen day (always at least 7 days away)
                days_ahead = (rec_day - today.weekday()) % 7 or 7
                next_date = today + timedelta(days=days_ahead)
                rec_order = RecurringOrder.objects.create(
                    customer=request.user,
                    delivery_address=form.cleaned_data['delivery_address'],
                    special_instructions=form.cleaned_data.get('special_instructions', ''),
                    recurrence_day=form.cleaned_data['recurrence_day'],
                    delivery_day=form.cleaned_data['delivery_day'],
                    next_order_date=next_date,
                )
                # Copy each item from the one-off order into the recurring template
                for item in order.items.all():
                    if item.product:
                        RecurringOrderItem.objects.create(
                            recurring_order=rec_order,
                            product=item.product,
                            quantity=item.quantity,
                            unit_price=item.unit_price,
                        )
                messages.success(request, f'Recurring order set up — next order scheduled for {next_date.strftime("%d %b %Y")}.')

            messages.success(request, f'Order #{order.id} placed successfully!')
            return redirect('home')
    else:
        # Pre-fill delivery address from the user's saved profile
        initial = {}
        if request.user.delivery_address:
            initial['delivery_address'] = request.user.delivery_address
        form = CheckoutForm(initial=initial, producers=producer_names)

    return render(request, 'marketplace/checkout.html', {
        'form': form,
        'cart': cart,
        'total': total,
        'commission': commission,
        'grand_total': grand_total,
    })


# ── Surplus produce ──────────────────────────────────────────────────────────

def surplus_list(request):  # TC-019: view active surplus listings
    # Only show listings that are still active and haven't passed their available_until time
    listings = SurplusProduce.objects.filter(
        is_active=True,
        available_until__gte=timezone.now()
    ).select_related('product', 'product__producer').order_by('available_until')
    return render(request, 'marketplace/surplus_list.html', {'listings': listings})


@login_required
def surplus_add(request):  # TC-019: producer creates a surplus listing with discount
    if request.user.role != 'producer':
        return redirect('home')
    if request.method == 'POST':
        form = SurplusProduceForm(request.POST)
        if form.is_valid():
            surplus = form.save(commit=False)
            surplus.save()
            messages.success(request, 'Surplus produce listed successfully.')
            return redirect('surplus_list')
    else:
        form = SurplusProduceForm()
        # Limit the product dropdown to only this producer's own active products
        form.fields['product'].queryset = Product.objects.filter(
            producer=request.user.producer_profile, is_active=True
        )
    return render(request, 'marketplace/surplus_form.html', {'form': form})


@login_required
def surplus_remove(request, pk):
    if request.method != 'POST' or request.user.role != 'producer':
        return redirect('surplus_list')
    surplus = get_object_or_404(SurplusProduce, pk=pk, product__producer=request.user.producer_profile)
    # Soft-delete: mark as inactive rather than deleting the record
    surplus.is_active = False
    surplus.save(update_fields=['is_active'])
    messages.success(request, 'Surplus listing removed.')
    return redirect('surplus_list')


@login_required
def surplus_cart_add(request, pk):  # TC-019: adds surplus item to cart at discounted price
    if request.method != 'POST':
        return redirect('surplus_list')
    surplus = get_object_or_404(SurplusProduce, pk=pk, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > surplus.quantity_available:
        messages.error(request, f'Only {surplus.quantity_available} available.')
        return redirect('surplus_list')
    cart = request.session.get('cart', {})
    product_id = str(surplus.product.id)
    if product_id in cart:
        cart[product_id]['quantity'] += quantity
    else:
        # Store the discounted price so it can't change after being added to cart
        cart[product_id] = {
            'name': f'{surplus.product.name} (Surplus Deal)',
            'price': str(surplus.discounted_price),
            'quantity': quantity,
            'producer': surplus.product.producer.business_name,
            'producer_postcode': surplus.product.producer.postcode,
        }
    request.session['cart'] = cart
    messages.success(request, f'"{surplus.product.name}" added to cart at £{surplus.discounted_price}.')
    return redirect('cart_view')


# ── Community board ──────────────────────────────────────────────────────────

def community_list(request):  # TC-020: community board — stories, recipes, storage tips
    posts = CommunityPost.objects.select_related('producer', 'product').order_by('-created_at')
    filter_type = request.GET.get('type', '')
    if filter_type:
        # Allow filtering by post type (story / recipe / storage tip)
        posts = posts.filter(post_type=filter_type)
    return render(request, 'marketplace/community.html', {'posts': posts, 'filter': filter_type})


@login_required
def community_add(request):  # TC-020: producer creates a story, recipe, or storage tip post
    if request.user.role != 'producer':
        return redirect('home')
    if request.method == 'POST':
        form = CommunityPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.producer = request.user.producer_profile
            post.save()
            messages.success(request, 'Post shared with the community.')
            return redirect('community_list')
    else:
        form = CommunityPostForm()
        # Restrict the product dropdown to only this producer's own products
        form.fields['product'].queryset = Product.objects.filter(
            producer=request.user.producer_profile, is_active=True
        )
        form.fields['product'].required = False
    return render(request, 'marketplace/community_form.html', {'form': form})


# ── Settlements (producer earnings) ─────────────────────────────────────────

@login_required
def settlements(request):  # TC-012: producer views weekly payment settlements
    if request.user.role != 'producer':
        return redirect('home')
    producer = request.user.producer_profile
    settlement_list = PaymentSettlement.objects.filter(producer=producer).order_by('-week_ending')
    total_net = sum(s.net_amount for s in settlement_list)
    return render(request, 'marketplace/settlements.html', {
        'settlements': settlement_list,
        'total_net': round(total_net, 2),
    })


@login_required
def settlements_export(request):  # TC-012: download settlements as CSV for tax reporting
    # Returns a downloadable CSV of all the producer's settlement records
    if request.user.role != 'producer':
        return redirect('home')
    producer = request.user.producer_profile
    settlement_list = PaymentSettlement.objects.filter(producer=producer).order_by('-week_ending')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="settlements.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order #', 'Week Ending', 'Gross (£)', 'Commission (£)', 'Net Payout (£)', 'Status'])
    for s in settlement_list:
        writer.writerow([s.order_id, s.week_ending, s.gross_amount, s.commission_deducted, s.net_amount, s.get_status_display()])
    return response


# ── Recall notices ───────────────────────────────────────────────────────────

def recall_list(request):
    # Public page — all visitors can see active recalls for food safety transparency
    recalls = RecallNotice.objects.select_related('product', 'issued_by').order_by('-created_at')
    return render(request, 'marketplace/recall_list.html', {'recalls': recalls})


@login_required
def recall_new(request):  # TC-018: producer issues a food safety recall notice
    if request.user.role != 'producer':
        return redirect('home')
    if request.method == 'POST':
        form = RecallNoticeForm(request.POST)
        if form.is_valid():
            recall = form.save(commit=False)
            recall.issued_by = request.user.producer_profile
            recall.status = 'issued'
            recall.save()
            # Log the recall issuance so there is an immutable record of when it happened
            AuditLog.objects.create(
                user=request.user,
                action=f'Recall issued for {recall.product.name}',
                resource_type='RecallNotice',
                resource_id=str(recall.id),
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, 'Recall notice issued.')
            return redirect('recall_detail', pk=recall.id)
    else:
        form = RecallNoticeForm()
        # Only allow the producer to recall their own products
        form.fields['product'].queryset = Product.objects.filter(
            producer=request.user.producer_profile
        )
    return render(request, 'marketplace/recall_form.html', {'form': form})


@login_required
def recall_detail(request, pk):  # TC-018: shows affected orders within the recall date range
    if request.user.role != 'producer':
        return redirect('home')
    recall = get_object_or_404(RecallNotice, pk=pk, issued_by=request.user.producer_profile)
    # Fetch the list of orders that contained this product in the affected date range
    affected_items = recall.get_affected_orders()
    return render(request, 'marketplace/recall_detail.html', {
        'recall': recall,
        'affected_items': affected_items,
    })


@login_required
def recurring_orders(request):  # TC-018: customer manages their recurring order templates
    orders = RecurringOrder.objects.filter(customer=request.user).prefetch_related('items__product').order_by('-created_at')
    return render(request, 'marketplace/recurring_orders.html', {'orders': orders})


@login_required
def recurring_order_cancel(request, pk):
    if request.method != 'POST':
        return redirect('recurring_orders')
    order = get_object_or_404(RecurringOrder, pk=pk, customer=request.user)
    order.is_active = False
    order.save(update_fields=['is_active'])
    messages.success(request, 'Recurring order cancelled.')
    return redirect('recurring_orders')


@login_required
def recurring_order_edit(request, pk):
    order = get_object_or_404(RecurringOrder, pk=pk, customer=request.user, is_active=True)
    items = order.items.select_related('product').all()
    if request.method == 'POST':
        for item in items:
            new_qty = request.POST.get(f'qty_{item.id}')
            if new_qty and int(new_qty) > 0:
                item.quantity = int(new_qty)
                item.save(update_fields=['quantity'])
        messages.success(request, 'Next order quantities updated.')
        return redirect('recurring_orders')
    return render(request, 'marketplace/recurring_order_edit.html', {'order': order, 'items': items})


@login_required
def my_orders(request):  # TC-021: customer order history; shows Write Review button on delivered orders
    orders = Order.objects.filter(customer=request.user).prefetch_related('items__product__producer').order_by('-created_at')
    reviewed_product_ids = set(
        Review.objects.filter(customer=request.user).values_list('product_id', flat=True)
    )
    return render(request, 'marketplace/my_orders.html', {
        'orders': orders,
        'reviewed_product_ids': reviewed_product_ids,
    })


@login_required
def reorder(request, pk):  # TC-021: re-adds available items from a past order to the cart
    if request.method != 'POST':
        return redirect('my_orders')
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    cart = request.session.get('cart', {})
    added = 0
    for item in order.items.select_related('product__producer').all():
        if item.product and item.product.is_active and item.product.stock > 0:
            product_id = str(item.product.id)
            if product_id in cart:
                cart[product_id]['quantity'] += item.quantity
            else:
                cart[product_id] = {
                    'name': item.product.name,
                    'price': str(item.product.price),
                    'quantity': item.quantity,
                    'producer': item.product.producer.business_name,
                    'producer_postcode': item.product.producer.postcode,
                }
            added += 1
    request.session['cart'] = cart
    if added:
        messages.success(request, f'{added} item(s) from Order #{order.id} added to your cart.')
    else:
        messages.error(request, 'No items from this order are currently available.')
    return redirect('cart_view')


@login_required
def order_list(request):  # TC-009: producer views incoming orders, filtered by status
    if request.user.role != 'producer':
        return redirect('home')
    producer = request.user.producer_profile
    status_filter = request.GET.get('status', '')
    orders = Order.objects.filter(items__product__producer=producer).distinct()
    if status_filter:
        orders = orders.filter(status=status_filter)
    orders = orders.order_by('delivery_date')
    return render(request, 'marketplace/order_list.html', {
        'orders': orders,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    })


@login_required
def order_detail(request, pk):  # TC-009: full order detail; TC-010: status update history
    if request.user.role != 'producer':
        return redirect('home')
    producer = request.user.producer_profile
    # items__product__producer traverses Order → OrderItem → Product → ProducerProfile
    # so a producer can only fetch orders that contain at least one of their products
    order = get_object_or_404(Order, pk=pk, items__product__producer=producer)
    items = order.items.filter(product__producer=producer).select_related('product')
    for item in items:
        item.subtotal = round(float(item.unit_price) * item.quantity, 2)
    # In a multi-vendor order this producer may have their own delivery date
    producer_delivery = order.producer_delivery_dates.filter(producer=producer).first()
    next_status = {
        'pending': 'confirmed',
        'confirmed': 'ready',
        'ready': 'delivered',
    }.get(order.status)
    history = AuditLog.objects.filter(
        resource_type='Order', resource_id=str(order.id)
    ).order_by('timestamp')
    return render(request, 'marketplace/order_detail.html', {
        'order': order,
        'items': items,
        'producer_delivery': producer_delivery,
        'next_status': next_status,
        'history': history,
    })


@login_required
def order_status_update(request, pk):  # TC-010: advances order through Pending → Confirmed → Ready → Delivered
    if request.method != 'POST' or request.user.role != 'producer':
        return redirect('order_list')
    producer = request.user.producer_profile
    order = get_object_or_404(Order, pk=pk, items__product__producer=producer)
    # Dictionary enforces the allowed progression — a producer can't skip stages or go backwards
    progression = {'pending': 'confirmed', 'confirmed': 'ready', 'ready': 'delivered'}
    new_status = progression.get(order.status)
    if new_status:
        order.status = new_status
        order.save()
        note = request.POST.get('note', '').strip()
        AuditLog.objects.create(
            user=request.user,
            action=f'Order #{order.id} status updated to {new_status}',
            resource_type='Order',
            resource_id=str(order.id),
            ip_address=request.META.get('REMOTE_ADDR'),
            notes=note,
        )
        messages.success(request, f'Order #{order.id} marked as {order.get_status_display()}.')
    return redirect('order_detail', pk=pk)


@login_required
def cart_update(request, pk):
    if request.method != 'POST':
        return redirect('cart_view')
    cart = request.session.get('cart', {})
    product_id = str(pk)
    quantity = int(request.POST.get('quantity', 1))
    if product_id in cart:
        if quantity > 0:
            cart[product_id]['quantity'] = quantity
        else:
            del cart[product_id]
    request.session['cart'] = cart
    return redirect('cart_view')


# ── Product reviews ──────────────────────────────────────────────────────────

@login_required
def review_submit(request, order_pk, product_pk):  # TC-024: verified purchase review — delivered orders only
    # status='delivered' in the query means this 404s if the order hasn't been delivered yet
    order = get_object_or_404(Order, pk=order_pk, customer=request.user, status='delivered')
    product = get_object_or_404(Product, pk=product_pk)
    # Verify the product was actually in this order — prevents reviewing items never purchased
    if not order.items.filter(product=product).exists():
        messages.error(request, 'You can only review products from your own delivered orders.')
        return redirect('my_orders')
    # One review per customer per product — the unique_together constraint on the model backs this up
    if Review.objects.filter(customer=request.user, product=product).exists():
        messages.error(request, 'You have already reviewed this product.')
        return redirect('my_orders')
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.customer = request.user
            review.product = product
            review.order = order
            review.save()
            messages.success(request, 'Review submitted. Thank you!')
            return redirect('product_detail', pk=product.id)
    else:
        form = ReviewForm()
    return render(request, 'marketplace/review_form.html', {
        'form': form,
        'product': product,
        'order': order,
    })


# ── Admin financial report ───────────────────────────────────────────────────

@login_required
def admin_report(request):  # TC-025: staff-only commission report with date filter, YTD totals, CSV export
    if not request.user.is_staff:
        return redirect('home')
    from datetime import date, timedelta
    date_from_str = request.GET.get('date_from', '')
    date_to_str = request.GET.get('date_to', '')
    try:
        date_from = date.fromisoformat(date_from_str)
    except ValueError:
        date_from = date.today() - timedelta(weeks=2)
    try:
        date_to = date.fromisoformat(date_to_str)
    except ValueError:
        date_to = date.today()

    settlements = PaymentSettlement.objects.filter(
        week_ending__gte=date_from,
        week_ending__lte=date_to,
    ).select_related('producer', 'order').order_by('week_ending', 'producer__business_name')

    total_gross = round(sum(float(s.gross_amount) for s in settlements), 2)
    total_commission = round(sum(float(s.commission_deducted) for s in settlements), 2)
    total_net = round(sum(float(s.net_amount) for s in settlements), 2)
    order_count = settlements.values('order_id').distinct().count()

    ytd_start = date(date.today().year, 1, 1)
    ytd_commission = round(
        sum(float(s.commission_deducted) for s in PaymentSettlement.objects.filter(week_ending__gte=ytd_start)),
        2,
    )

    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="commission_{date_from}_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order #', 'Producer', 'Week Ending', 'Gross (£)', 'Commission (£)', 'Net Payout (£)', 'Status'])
        for s in settlements:
            writer.writerow([s.order_id, s.producer.business_name, s.week_ending,
                             s.gross_amount, s.commission_deducted, s.net_amount, s.get_status_display()])
        return response

    return render(request, 'marketplace/admin_report.html', {
        'settlements': settlements,
        'total_gross': total_gross,
        'total_commission': total_commission,
        'total_net': total_net,
        'order_count': order_count,
        'ytd_commission': ytd_commission,
        'date_from': date_from,
        'date_to': date_to,
    })


# ── Order receipt ────────────────────────────────────────────────────────────

@login_required
def order_receipt(request, pk):  # TC-021: printable receipt for a past order
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    items = order.items.select_related('product__producer').all()
    for item in items:
        item.subtotal = round(float(item.unit_price) * item.quantity, 2)
    return render(request, 'marketplace/order_receipt.html', {
        'order': order,
        'items': items,
    })
