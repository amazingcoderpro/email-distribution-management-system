# Generated by Django 2.1 on 2019-07-20 14:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0019_auto_20190720_1457'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='customer_group_list',
            field=models.TextField(default='x', verbose_name='邮件对应的客户组列表'),
            preserve_default=False,
        ),
    ]
