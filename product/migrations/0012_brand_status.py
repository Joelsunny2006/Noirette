# Generated by Django 5.1.3 on 2024-11-28 14:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0011_remove_productimage_image_url1_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='brand',
            name='status',
            field=models.BooleanField(default=True),
        ),
    ]