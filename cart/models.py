from django.db import models
from category.models import Category
from product.models import *
from users.models import *
from coupon.models import *


class Cart(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    applied_coupon = models.ForeignKey(
        Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='carts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def total_price(self):
        return sum(item.total_price() for item in self.items.all())

    def total_price_after_discount(self):
        # Apply coupon discount if applicable
        total = self.total_price()
        if self.applied_coupon:
            total = self.applied_coupon.apply_discount(total)
        return total


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, related_name='cart_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'variant')  # Ensures no duplicates for same variant in the same cart

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.name} ({self.variant.variant_name})"

    def total_price(self):
        # Use the discounted price if available
        price_per_item = self.variant.get_discounted_price() or self.variant.variant_price
        return price_per_item * self.quantity


class Wishlist(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('product.Variant', on_delete=models.CASCADE)  # Reference to Variant
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'variant')  # Prevent duplicate variants in the wishlist

    def __str__(self):
        return f"{self.variant.name} in {self.wishlist.user.username}'s wishlist"

