# Generated by Django 2.1 on 2019-07-31 13:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0085_remove_checkoutevent_email_date'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='checkoutevent',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='customer',
            options={'managed': False},
        ),
    ]
