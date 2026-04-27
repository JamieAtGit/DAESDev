from django.contrib.auth.models import AbstractUser
from django.db import models


# Extends Django's built-in user model to add a role field and delivery details
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


# Stores the public-facing business information for a producer user
class ProducerProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='producer_profile'
    )
    business_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.TextField()
    postcode = models.CharField(max_length=10)  # used to calculate food miles

    def __str__(self):
        return self.business_name


# Simple product categories (e.g. Vegetables, Dairy) used to filter the marketplace
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)  # URL-friendly version of the name
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


# A product listed by a producer on the marketplace
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
    seasonal_months = models.CharField(max_length=200, blank=True)  # e.g. "October – February"
    lead_time_hours = models.PositiveIntegerField(default=48)  # minimum notice needed before delivery
    low_stock_threshold = models.PositiveIntegerField(default=10)  # alert producer when stock falls to or below this; 0 = disabled
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} — {self.producer.business_name}"


# A time-limited discounted listing for produce that needs to be sold quickly
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
        # Calculate how much cheaper the surplus price is as a percentage
        if self.original_price:
            saving = self.original_price - self.discounted_price
            return round((saving / self.original_price) * 100)
        return 0


# A post shared by a producer — can be a farm story, recipe, or storage tip
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


# Records how much each producer is owed after a 5% platform commission is deducted
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
    week_ending = models.DateField()  # settlements are grouped by the week they fall in
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Settlement for {self.producer.business_name} — week ending {self.week_ending}"


# A tamper-evident log of important actions (orders placed, statuses changed, recalls issued)
class AuditLog(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=100, blank=True)  # e.g. 'Order', 'RecallNotice'
    resource_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} — {self.action}"


# A food safety recall notice raised by a producer for one of their products
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
    affected_from = models.DateField(null=True, blank=True)  # date range used to identify affected orders
    affected_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Recall: {self.product.name} — {self.status}"

    def get_affected_orders(self):
        # Find all order items for this product that fall within the affected date range
        from django.db.models import Q
        qs = OrderItem.objects.filter(product=self.product).select_related('order', 'order__customer')
        if self.affected_from:
            qs = qs.filter(order__created_at__date__gte=self.affected_from)
        if self.affected_to:
            qs = qs.filter(order__created_at__date__lte=self.affected_to)
        return qs


# A standing weekly order template — the platform uses this to generate orders automatically
class RecurringOrder(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'),
    ]
    customer = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='recurring_orders')
    delivery_address = models.TextField()
    special_instructions = models.TextField(blank=True)
    recurrence_day = models.CharField(max_length=20, choices=DAY_CHOICES)  # day the order is placed
    delivery_day = models.CharField(max_length=20, choices=DAY_CHOICES)    # day delivery is expected
    is_active = models.BooleanField(default=True)
    next_order_date = models.DateField()  # date the next auto-order should be generated
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recurring order for {self.customer.username} every {self.recurrence_day}"


# The individual product lines within a recurring order template
class RecurringOrderItem(models.Model):
    recurring_order = models.ForeignKey(RecurringOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)  # price locked at time of setup

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


# A customer's completed purchase — contains delivery details and the total charged
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
    total_price = models.DecimalField(max_digits=10, decimal_places=2)  # includes commission
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_address = models.TextField()
    delivery_date = models.DateField()
    special_instructions = models.TextField(blank=True)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Order #{self.id} by {self.customer.username}"


# A single product line within an order, with the quantity and price at time of purchase
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order #{self.order.id}"


# A verified product review — only customers who received the product can submit one
class Review(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()  # 1–5 stars
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'product')  # one review per customer per product

    def __str__(self):
        return f"{self.rating}★ — {self.product.name} by {self.customer.username}"
