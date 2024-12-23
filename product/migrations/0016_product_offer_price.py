# Generated by Django 5.1.3 on 2024-12-16 07:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("product", "0015_remove_product_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="offer_price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
    ]