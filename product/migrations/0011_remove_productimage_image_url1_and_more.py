# Generated by Django 5.1.3 on 2024-11-27 13:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0010_brand_product_brand'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productimage',
            name='image_url1',
        ),
        migrations.RemoveField(
            model_name='productimage',
            name='image_url2',
        ),
        migrations.RemoveField(
            model_name='productimage',
            name='image_url3',
        ),
        migrations.AddField(
            model_name='productimage',
            name='image_url',
            field=models.ImageField(blank=True, null=True, upload_to='products/images/'),
        ),
    ]
