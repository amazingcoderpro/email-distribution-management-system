# Generated by Django 2.1 on 2019-07-23 14:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0033_dashboard_total_unsubscribe'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dashboard',
            old_name='total_conversion_rate',
            new_name='avg_conversion_rate',
        ),
        migrations.RenameField(
            model_name='dashboard',
            old_name='total_repeat_purchase_rate',
            new_name='avg_repeat_purchase_rate',
        ),
        migrations.AddField(
            model_name='dashboard',
            name='total_sessions',
            field=models.IntegerField(blank=True, null=True, verbose_name='sessions总量'),
        ),
    ]
