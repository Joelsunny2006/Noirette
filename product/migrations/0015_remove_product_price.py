# Generated by Django 5.1.3 on 2024-12-04 04:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0014_remove_product_stock'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='price',
        ),
    ]
