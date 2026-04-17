from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('producer', 'Producer'),
        ('community_group', 'Community Group'),
        ('restaurant', 'Restaurant'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=20, blank=True)
    delivery_address = models.TextField(blank=True)
    delivery_postcode = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class ProducerProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='producer_profile'
    )
    business_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.TextField()
    postcode = models.CharField(max_length=10)

    def __str__(self):
        return self.business_name


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    producer = models.ForeignKey(
        ProducerProfile, on_delete=models.CASCADE, related_name='products'
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    allergens = models.TextField(blank=True)
    is_organic = models.BooleanField(default=False)
    harvest_date = models.DateField(null=True, blank=True)
    best_before = models.DateField(null=True, blank=True)
    farm_origin = models.CharField(max_length=200, blank=True)
    is_seasonal = models.BooleanField(default=False)
    seasonal_months = models.CharField(max_length=200, blank=True)
    lead_time_hours = models.PositiveIntegerField(default=48)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} — {self.producer.business_name}"


class SurplusProduce(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='surplus_listings')
    original_price = models.DecimalField(max_digits=8, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity_available = models.PositiveIntegerField()
    reason = models.TextField(blank=True, help_text='e.g. End of day surplus, slight cosmetic imperfections')
    available_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Surplus: {self.product.name} at £{self.discounted_price}"

    @property
    def discount_percentage(self):
        if self.original_price:
            saving = self.original_price - self.discounted_price
            return round((saving / self.original_price) * 100)
        return 0


class CommunityPost(models.Model):
    POST_TYPE_CHOICES = [
        ('story', 'Farm Story'),
        ('recipe', 'Recipe'),
        ('storage', 'Storage Tip'),
    ]
    producer = models.ForeignKey(ProducerProfile, on_delete=models.CASCADE, related_name='community_posts')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='community_posts')
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_post_type_display()} — {self.title}"


class PaymentSettlement(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    producer = models.ForeignKey(ProducerProfile, on_delete=models.CASCADE, related_name='settlements')
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='settlements')
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_deducted = models.DecimalField(max_digits=10, decimal_places=2)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    week_ending = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Settlement for {self.producer.business_name} — week ending {self.week_ending}"


class AuditLog(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} — {self.action}"


class RecallNotice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('resolved', 'Resolved'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='recalls')
    issued_by = models.ForeignKey(ProducerProfile, on_delete=models.CASCADE, related_name='recalls')
    reason = models.TextField()
    batch_info = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    affected_from = models.DateField(null=True, blank=True)
    affected_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Recall: {self.product.name} — {self.status}"

    def get_affected_orders(self):
        from django.db.models import Q
        qs = OrderItem.objects.filter(product=self.product).select_related('order', 'order__customer')
        if self.affected_from:
            qs = qs.filter(order__created_at__date__gte=self.affected_from)
        if self.affected_to:
            qs = qs.filter(order__created_at__date__lte=self.affected_to)
        return qs



class RecurringOrder(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'),
    ]
    customer = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='recurring_orders')
    delivery_address = models.TextField()
    special_instructions = models.TextField(blank=True)
    recurrence_day = models.CharField(max_length=20, choices=DAY_CHOICES)
    delivery_day = models.CharField(max_length=20, choices=DAY_CHOICES)
    is_active = models.BooleanField(default=True)
    next_order_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recurring order for {self.customer.username} every {self.recurrence_day}"


class RecurringOrderItem(models.Model):
    recurring_order = models.ForeignKey(RecurringOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('ready', 'Ready for Delivery'),
        ('delivered', 'Delivered'),
    ]
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_address = models.TextField()
    delivery_date = models.DateField()
    special_instructions = models.TextField(blank=True)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Order #{self.id} by {self.customer.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order #{self.order.id}"
