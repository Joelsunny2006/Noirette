# Generated by Django 5.1.3 on 2024-11-26 15:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0004_alter_productimage_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productimage',
            name='image_url1',
            field=models.ImageField(blank=True, null=True, upload_to='products/images/'),
        ),
        migrations.AlterField(
            model_name='productimage',
            name='image_url2',
            field=models.ImageField(blank=True, null=True, upload_to='products/images/'),
        ),
        migrations.AlterField(
            model_name='productimage',
            name='image_url3',
            field=models.ImageField(blank=True, null=True, upload_to='products/images/'),
        ),
    ]
