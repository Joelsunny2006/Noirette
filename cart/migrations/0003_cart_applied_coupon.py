# Generated by Django 5.1.3 on 2024-12-16 12:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0002_wishlist_wishlistitem"),
        ("coupon", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cart",
            name="applied_coupon",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="carts",
                to="coupon.coupon",
            ),
        ),
    ]
