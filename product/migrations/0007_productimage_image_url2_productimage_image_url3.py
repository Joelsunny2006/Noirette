# Generated by Django 5.1.3 on 2024-11-27 07:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0006_rename_image_url1_productimage_image_url_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimage',
            name='image_url2',
            field=models.ImageField(blank=True, null=True, upload_to='products/images/'),
        ),
        migrations.AddField(
            model_name='productimage',
            name='image_url3',
            field=models.ImageField(blank=True, null=True, upload_to='products/images/'),
        ),
    ]