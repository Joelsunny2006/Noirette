from django.db import models
from users.models import UserProfile
from product.models import Product
from django.db import models
from product.models import *
class OrderAddress(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)  # Link to the logged-in user
    name = models.CharField(max_length=200)  # Full name
    phone_number = models.CharField(max_length=20)  # Phone number
    house_name = models.CharField(max_length=100, blank=True)  # Optional field
    street_name = models.CharField(max_length=255)  # Street address
    district = models.CharField(max_length=100)  # City or area
    state = models.CharField(max_length=100)  # State
    country = models.CharField(max_length=100, default="Unknown")  # Default value as fallback
    pin_number = models.CharField(max_length=20)  # Postal code or PIN

    def __str__(self):
        return f"{self.name}, {self.street_name}, {self.district}, {self.state}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('Payment Failed', 'Payment Failed'),
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('razorpay', 'Razorpay'),
        ('cash on delivery', 'Cash On Delivery'),
        ('wallet', 'Wallet'),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    # New fields
    order_address = models.ForeignKey(
        OrderAddress, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name="order_addresses"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.variant.variant_name} (Order #{self.order.id})"

class Address(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    # address_type = models.CharField(max_length=100, default="billing")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    street_address = models.CharField(max_length=255)
    apartment = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}, {self.street_address}, {self.city}, {self.postcode}"




