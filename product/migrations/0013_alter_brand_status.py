# Generated by Django 5.1.3 on 2024-11-30 13:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0012_brand_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brand',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active', max_length=20),
        ),
    ]
