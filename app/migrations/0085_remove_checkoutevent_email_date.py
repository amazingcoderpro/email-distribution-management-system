# Generated by Django 2.1 on 2019-07-31 13:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0084_auto_20190731_1149'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='checkoutevent',
            name='email_date',
        ),
    ]
