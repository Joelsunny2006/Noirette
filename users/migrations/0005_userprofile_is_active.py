# Generated by Django 5.1.3 on 2024-12-09 03:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_remove_userprofile_confirm_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_active",
            field=models.BooleanField(default=False),
        ),
    ]
