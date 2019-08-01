# Generated by Django 2.1 on 2019-08-01 14:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0109_customergroup_open_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailtrigger',
            name='open_rate',
            field=models.DecimalField(decimal_places=5, default=0.0, max_digits=5, verbose_name='邮件打开率'),
        ),
    ]
