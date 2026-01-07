# Generated manually
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProxyConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('listen_port', models.IntegerField(unique=True, verbose_name='监听端口')),
                ('is_running', models.BooleanField(default=False, verbose_name='运行状态')),
                ('gost_pid', models.IntegerField(blank=True, null=True, verbose_name='Gost进程ID')),
                ('auto_start', models.BooleanField(default=True, verbose_name='自动启动')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='proxyconfig', to='accounts.l2tpaccount', verbose_name='关联账号')),
            ],
            options={
                'verbose_name': '代理配置',
                'verbose_name_plural': '代理配置',
                'db_table': 'proxy_configs',
                'ordering': ['listen_port'],
            },
        ),
        migrations.CreateModel(
            name='RoutingTable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('table_id', models.IntegerField(unique=True, verbose_name='路由表ID')),
                ('table_name', models.CharField(max_length=32, unique=True, verbose_name='路由表名')),
                ('interface', models.CharField(blank=True, default='', max_length=16, verbose_name='绑定接口')),
                ('is_active', models.BooleanField(default=False, verbose_name='是否激活')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='routing_table', to='accounts.l2tpaccount', verbose_name='关联账号')),
            ],
            options={
                'verbose_name': '路由表',
                'verbose_name_plural': '路由表',
                'db_table': 'routing_tables',
                'ordering': ['table_id'],
            },
        ),
    ]
