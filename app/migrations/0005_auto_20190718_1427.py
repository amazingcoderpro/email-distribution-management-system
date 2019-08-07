# Generated by Django 2.1 on 2019-07-18 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_auto_20190718_1427'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderevent',
            name='order_update_time',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='订单更新时间'),
        ),
        migrations.AddField(
            model_name='orderevent',
            name='update_time',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='更新时间'),
        ),
        migrations.AlterField(
            model_name='orderevent',
            name='create_time',
            field=models.DateTimeField(db_index=True, verbose_name='创建时间'),
        ),
        migrations.AlterField(
            model_name='orderevent',
            name='order_create_time',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='订单创建时间'),
        ),
        migrations.AlterUniqueTogether(
            name='orderevent',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='orderevent',
            name='store_id',
        ),
    ]
