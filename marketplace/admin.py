from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ProducerProfile, Category, Product, Order, OrderItem, SurplusProduce


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )
    list_display = ['username', 'email', 'role', 'is_staff']
    list_filter = ['role']


@admin.register(ProducerProfile)
class ProducerProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'postcode']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'producer', 'category', 'price', 'stock', 'is_active']
    list_filter = ['is_active', 'is_organic', 'category']
    search_fields = ['name', 'description']


@admin.register(SurplusProduce)
class SurplusProduceAdmin(admin.ModelAdmin):
    list_display = ['product', 'discounted_price', 'discount_percentage', 'quantity_available', 'available_until', 'is_active']
    list_filter = ['is_active']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'status', 'total_price', 'commission_amount', 'delivery_date']
    list_filter = ['status']
    inlines = [OrderItemInline]
