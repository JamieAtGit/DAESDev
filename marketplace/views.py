from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, ProducerRegistrationForm, ProductForm
from .models import ProducerProfile, Product


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
