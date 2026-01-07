# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='L2TPAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=64, unique=True, verbose_name='用户名')),
                ('password', models.CharField(max_length=128, verbose_name='密码')),
                ('assigned_ip', models.GenericIPAddressField(unique=True, verbose_name='分配IP')),
                ('is_active', models.BooleanField(default=True, verbose_name='启用状态')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': 'L2TP账号',
                'verbose_name_plural': 'L2TP账号',
                'db_table': 'l2tp_accounts',
                'ordering': ['-created_at'],
            },
        ),
    ]
