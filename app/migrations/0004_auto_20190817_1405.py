# Generated by Django 2.1 on 2019-08-17 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_auto_20190817_1405'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='logo',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='邮件logo'),
        ),
        migrations.AddField(
            model_name='store',
            name='service_email',
            field=models.EmailField(blank=True, max_length=255, null=True, verbose_name='service_email'),
        ),
    ]
