# Generated by Django 2.1 on 2019-07-11 02:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_store_timezone'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='store_view_id',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='店铺的GA中的view id'),
        ),
    ]
