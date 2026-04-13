import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, ProducerRegistrationForm, ProductForm, CheckoutForm, CommunityPostForm, RecallNoticeForm
from .models import ProducerProfile, Product, Category, Order, OrderItem, SurplusProduce, CommunityPost, PaymentSettlement, AuditLog, RecallNotice
from .surplus_forms import SurplusProduceForm
from .food_miles import calculate_food_miles
from django.utils import timezone
from django.shortcuts import get_object_or_404


def home(request):
    return render(request, 'marketplace/home.html')


def register(request):
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


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'marketplace/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


def register_producer(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = ProducerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'producer'
            user.save()
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


@login_required
def dashboard(request):
    if request.user.role != 'producer':
        return redirect('home')
    profile, _ = ProducerProfile.objects.get_or_create(user=request.user)
    products = Product.objects.filter(producer=profile).order_by('-created_at')
    return render(request, 'marketplace/dashboard.html', {'products': products, 'profile': profile})


@login_required
def product_create(request):
    if request.user.role != 'producer':
        return redirect('home')
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = request.user.producer_profile
            product.save()
            messages.success(request, f'Product "{product.name}" created.')
            return redirect('dashboard')
    else:
        form = ProductForm()
    return render(request, 'marketplace/product_form.html', {'form': form, 'action': 'Create'})


@login_required
def product_edit(request, pk):
    if request.user.role != 'producer':
        return redirect('home')
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


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('producer', 'category')
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    organic = request.GET.get('organic', '')

    if search:
        products = products.filter(name__icontains=search) | products.filter(description__icontains=search)
    if category:
        products = products.filter(category__slug=category)
    if organic:
        products = products.filter(is_organic=True)

    return render(request, 'marketplace/product_list.html', {
        'products': products,
        'categories': Category.objects.all(),
        'search': search,
        'category': category,
        'organic': organic,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    food_miles = None
    if product.producer.postcode:
        food_miles = calculate_food_miles('BS11AA', product.producer.postcode)
    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'food_miles': food_miles,
    })


@login_required
def cart_add(request, pk):
    if request.method != 'POST':
        return redirect('product_list')
    product = get_object_or_404(Product, pk=pk, is_active=True)
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    product_id = str(pk)
    if product_id in cart:
        cart[product_id]['quantity'] += quantity
    else:
        cart[product_id] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': quantity,
            'producer': product.producer.business_name,
        }
    request.session['cart'] = cart
    messages.success(request, f'"{product.name}" added to cart.')
    return redirect('cart_view')


@login_required
def cart_view(request):
    cart = request.session.get('cart', {})
    for item in cart.values():
        item['subtotal'] = round(float(item['price']) * item['quantity'], 2)
    total = round(sum(item['subtotal'] for item in cart.values()), 2)
    return render(request, 'marketplace/cart.html', {'cart': cart, 'total': total})


@login_required
def cart_remove(request, pk):
    if request.method != 'POST':
        return redirect('cart_view')
    cart = request.session.get('cart', {})
    cart.pop(str(pk), None)
    request.session['cart'] = cart
    return redirect('cart_view')


@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('cart_view')

    for item in cart.values():
        item['subtotal'] = round(float(item['price']) * item['quantity'], 2)

    total = round(sum(item['subtotal'] for item in cart.values()), 2)
    commission = round(total * 0.05, 2)
    grand_total = round(total + commission, 2)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                customer=request.user,
                delivery_address=form.cleaned_data['delivery_address'],
                delivery_date=form.cleaned_data['delivery_date'],
                total_price=grand_total,
                commission_amount=commission,
            )
            for product_id, item in cart.items():
                product = get_object_or_404(Product, pk=int(product_id))
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    unit_price=item['price'],
                )
            del request.session['cart']

            # create per-producer settlement records
            from datetime import date, timedelta
            week_ending = date.today() + timedelta(days=(6 - date.today().weekday()))
            producers_in_order = set()
            for item in order.items.all():
                if item.product:
                    producers_in_order.add(item.product.producer)
            for producer in producers_in_order:
                producer_items = order.items.filter(product__producer=producer)
                gross = sum(float(i.unit_price) * i.quantity for i in producer_items)
                commission = round(gross * 0.05, 2)
                net = round(gross - commission, 2)
                PaymentSettlement.objects.create(
                    producer=producer,
                    order=order,
                    gross_amount=gross,
                    commission_deducted=commission,
                    net_amount=net,
                    week_ending=week_ending,
                )

            # audit log
            AuditLog.objects.create(
                user=request.user,
                action=f'Order #{order.id} placed',
                resource_type='Order',
                resource_id=str(order.id),
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            messages.success(request, f'Order #{order.id} placed successfully!')
            return redirect('home')
    else:
        form = CheckoutForm()

    return render(request, 'marketplace/checkout.html', {
        'form': form,
        'cart': cart,
        'total': total,
        'commission': commission,
        'grand_total': grand_total,
    })


def surplus_list(request):
    listings = SurplusProduce.objects.filter(
        is_active=True,
        available_until__gte=timezone.now()
    ).select_related('product', 'product__producer').order_by('available_until')
    return render(request, 'marketplace/surplus_list.html', {'listings': listings})


@login_required
def surplus_add(request):
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
        form.fields['product'].queryset = Product.objects.filter(
            producer=request.user.producer_profile, is_active=True
        )
    return render(request, 'marketplace/surplus_form.html', {'form': form})


def community_list(request):
    posts = CommunityPost.objects.select_related('producer', 'product').order_by('-created_at')
    filter_type = request.GET.get('type', '')
    if filter_type:
        posts = posts.filter(post_type=filter_type)
    return render(request, 'marketplace/community.html', {'posts': posts, 'filter': filter_type})


@login_required
def community_add(request):
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
        form.fields['product'].queryset = Product.objects.filter(
            producer=request.user.producer_profile, is_active=True
        )
        form.fields['product'].required = False
    return render(request, 'marketplace/community_form.html', {'form': form})


@login_required
def settlements(request):
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
def settlements_export(request):
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


def recall_list(request):
    recalls = RecallNotice.objects.select_related('product', 'issued_by').order_by('-created_at')
    return render(request, 'marketplace/recall_list.html', {'recalls': recalls})


@login_required
def recall_new(request):
    if request.user.role != 'producer':
        return redirect('home')
    if request.method == 'POST':
        form = RecallNoticeForm(request.POST)
        if form.is_valid():
            recall = form.save(commit=False)
            recall.issued_by = request.user.producer_profile
            recall.status = 'issued'
            recall.save()
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
        form.fields['product'].queryset = Product.objects.filter(
            producer=request.user.producer_profile
        )
    return render(request, 'marketplace/recall_form.html', {'form': form})


@login_required
def recall_detail(request, pk):
    if request.user.role != 'producer':
        return redirect('home')
    recall = get_object_or_404(RecallNotice, pk=pk, issued_by=request.user.producer_profile)
    affected_items = recall.get_affected_orders()
    return render(request, 'marketplace/recall_detail.html', {
        'recall': recall,
        'affected_items': affected_items,
    })


@login_required
def my_orders(request):
    orders = Order.objects.filter(customer=request.user).prefetch_related('items__product').order_by('-created_at')
    return render(request, 'marketplace/my_orders.html', {'orders': orders})


@login_required
def order_list(request):
    if request.user.role != 'producer':
        return redirect('home')
    producer = request.user.producer_profile
    orders = Order.objects.filter(
        items__product__producer=producer
    ).distinct().order_by('delivery_date')
    return render(request, 'marketplace/order_list.html', {'orders': orders})


@login_required
def order_detail(request, pk):
    if request.user.role != 'producer':
        return redirect('home')
    producer = request.user.producer_profile
    order = get_object_or_404(Order, pk=pk, items__product__producer=producer)
    items = order.items.filter(product__producer=producer).select_related('product')
    next_status = {
        'pending': 'confirmed',
        'confirmed': 'ready',
        'ready': 'delivered',
    }.get(order.status)
    return render(request, 'marketplace/order_detail.html', {
        'order': order,
        'items': items,
        'next_status': next_status,
    })


@login_required
def order_status_update(request, pk):
    if request.method != 'POST' or request.user.role != 'producer':
        return redirect('order_list')
    producer = request.user.producer_profile
    order = get_object_or_404(Order, pk=pk, items__product__producer=producer)
    progression = {'pending': 'confirmed', 'confirmed': 'ready', 'ready': 'delivered'}
    new_status = progression.get(order.status)
    if new_status:
        order.status = new_status
        order.save()
        AuditLog.objects.create(
            user=request.user,
            action=f'Order #{order.id} status updated to {new_status}',
            resource_type='Order',
            resource_id=str(order.id),
            ip_address=request.META.get('REMOTE_ADDR'),
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
