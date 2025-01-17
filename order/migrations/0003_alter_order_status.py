# Generated by Django 5.1.3 on 2024-12-17 18:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0002_remove_address_address_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("Payment Failed", "Payment Failed"),
                    ("Pending", "Pending"),
                    ("Processing", "Processing"),
                    ("Shipped", "Shipped"),
                    ("Completed", "Completed"),
                    ("Cancelled", "Cancelled"),
                    ("Returned", "Returned"),
                ],
                default="Pending",
                max_length=20,
            ),
        ),
    ]
