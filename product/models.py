from django.db import models
from django.utils.text import slugify
from django.contrib.postgres.fields import ArrayField
from category.models import Category
from decimal import Decimal

class Brand(models.Model):
    name = models.CharField(max_length=200, unique=True)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )

    def __str__(self):
        return self.name


class Product(models.Model):
    serial_number = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, null=False)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.CASCADE)
    description = models.TextField()
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    home_display = models.BooleanField(default=False)
    brand = models.ForeignKey(Brand, related_name="products", on_delete=models.CASCADE, null=True, blank=True)
    offer_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0.00)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.serial_number} - {self.name}"


class Variant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    variant_name = models.CharField(max_length=200)
    variant_price = models.DecimalField(max_digits=10, decimal_places=2)
    variant_stock = models.IntegerField(default=0)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def get_discounted_price(self):
        if self.product.offer_percentage:
            discount = (self.variant_price * self.product.offer_percentage) / Decimal('100')
            return round(self.variant_price - discount, 2)
        return self.variant_price


    def save(self, *args, **kwargs):
        self.discounted_price = self.get_discounted_price()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.variant_name}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE
    )
    image_url = models.ImageField(upload_to="products/images/", null=True, blank=True)

    def __str__(self):
        return f"Images for {self.product.name}"

    # class Meta:
    #     ordering = ['image_order']