# Generated by Django 2.1 on 2019-08-01 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0094_auto_20190801_1016'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='orderevent',
            options={'managed': False},
        ),
        migrations.RemoveField(
            model_name='emailtrigger',
            name='store',
        ),
        migrations.AddField(
            model_name='emailtrigger',
            name='store_id',
            field=models.IntegerField(default=1, verbose_name='店铺id'),
            preserve_default=False,
        ),
    ]
