# Generated by Django 2.1 on 2019-07-31 13:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0087_auto_20190731_1348'),
    ]

    operations = [
        migrations.AddField(
            model_name='checkoutevent',
            name='email_date',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='最后一次邮件通知时间，为空代表还没有发送过促销邮件'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='unsubscribe_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='取消订阅时间/休眠的截止时间'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='unsubscribe_status',
            field=models.SmallIntegerField(choices=[(0, 'is false'), (1, 'is true'), (2, 'is sleep')], db_index=True, default=0, verbose_name='取消订阅或者休眠'),
        ),
    ]
