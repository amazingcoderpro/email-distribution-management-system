# Generated by Django 2.1 on 2019-08-03 09:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0121_auto_20190803_0955'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dashboard',
            name='total_revenue',
            field=models.FloatField(default=0, verbose_name='Revenue'),
        ),
    ]
