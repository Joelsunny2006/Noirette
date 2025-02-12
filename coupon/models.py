from django.db import models
from django.utils import timezone
from decimal import Decimal

class Coupon(models.Model):
    CODE_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('upcoming', 'Upcoming'),
        ('expired', 'Expired')
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=CODE_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    current_usage = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    

    def is_valid(self):
        now = timezone.now()
        return (
            self.status == 'active' and 
            self.valid_from <= now <= self.valid_to and
            (self.usage_limit is None or self.current_usage < self.usage_limit)
        )

    def apply_discount(self, total_amount):
        if not self.is_valid():
            return total_amount

        if self.discount_type == 'percentage':
            discount = total_amount * (self.discount_value / 100)
        else:  # fixed amount
            discount = min(self.discount_value, total_amount)

        return max(total_amount - discount, 0)

    def __str__(self):
        return f"{self.code} - {self.get_discount_type_display()}"
    
    @property
    def total_discount_given(self):
        """Calculate total discount amount given by this coupon"""
        return self.orders.aggregate(
            total_discount=models.Sum('coupon_discount')
        )['total_discount'] or Decimal('0.00')

    @property
    def total_orders_used(self):
        """Get total number of orders where this coupon was used"""
        return self.orders.count()

    @property
    def average_discount_per_order(self):
        """Calculate average discount per order"""
        if self.total_orders_used == 0:
            return Decimal('0.00')
        return self.total_discount_given / self.total_orders_used