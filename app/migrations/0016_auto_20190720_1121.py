# Generated by Django 2.1 on 2019-07-20 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0015_auto_20190720_1121'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderevent',
            name='status_tag',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='订单类型tag'),
        ),
        migrations.AddField(
            model_name='orderevent',
            name='status_url',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='订单类型url'),
        ),
    ]
