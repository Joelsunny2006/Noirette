# Generated by Django 5.1.3 on 2024-11-14 07:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_remove_userprofile_is_active_userprofile_is_blocked'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='confirm_password',
        ),
    ]
