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
            name='SystemLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('info', '信息'), ('warning', '警告'), ('error', '错误'), ('debug', '调试')], default='info', max_length=16, verbose_name='日志级别')),
                ('log_type', models.CharField(choices=[('connection', '连接'), ('proxy', '代理'), ('routing', '路由'), ('system', '系统'), ('l2tp', 'L2TP')], max_length=16, verbose_name='日志类型')),
                ('message', models.TextField(verbose_name='日志消息')),
                ('details', models.JSONField(blank=True, null=True, verbose_name='详细信息')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')),
                ('interface', models.CharField(blank=True, default='', max_length=16, verbose_name='接口名')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs', to='accounts.l2tpaccount', verbose_name='关联账号')),
            ],
            options={
                'verbose_name': '系统日志',
                'verbose_name_plural': '系统日志',
                'db_table': 'system_logs',
                'ordering': ['-created_at'],
            },
        ),
    ]
