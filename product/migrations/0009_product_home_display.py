# Generated by Django 5.1.3 on 2024-11-27 10:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0008_rename_image_url_productimage_image_url1'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='home_display',
            field=models.BooleanField(default=False),
        ),
    ]