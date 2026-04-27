from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ProducerProfile, Category, Product, Order, OrderItem, SurplusProduce, CommunityPost, PaymentSettlement, AuditLog, RecallNotice


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Extend the default UserAdmin fieldsets to expose the role field
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
    list_display = ['product', 'discounted_price', 'quantity_available', 'available_until', 'is_active']
    list_filter = ['is_active']


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'post_type', 'producer', 'product', 'created_at']
    list_filter = ['post_type']


@admin.register(PaymentSettlement)
class PaymentSettlementAdmin(admin.ModelAdmin):
    list_display = ['producer', 'order', 'gross_amount', 'commission_deducted', 'net_amount', 'status', 'week_ending']
    list_filter = ['status', 'week_ending']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'resource_type', 'resource_id']
    # All fields are read-only — the audit log must never be edited through the admin
    readonly_fields = ['timestamp', 'user', 'action', 'resource_type', 'resource_id', 'ip_address', 'notes']


@admin.register(RecallNotice)
class RecallNoticeAdmin(admin.ModelAdmin):
    list_display = ['product', 'issued_by', 'status', 'affected_from', 'affected_to', 'created_at']
    list_filter = ['status']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'status', 'total_price', 'commission_amount', 'delivery_date']
    list_filter = ['status']
    inlines = [OrderItemInline]
