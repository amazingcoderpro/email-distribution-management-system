# Generated by Django 2.1 on 2019-08-01 11:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0105_auto_20190801_1136'),
    ]

    operations = [
        migrations.RenameField(
            model_name='emailtemplate',
            old_name='state',
            new_name='status',
        ),
        migrations.AddField(
            model_name='emailtemplate',
            name='enable',
            field=models.SmallIntegerField(choices=[(0, '禁用'), (1, '启用')], default=0, verbose_name='是否启用'),
        ),
    ]
