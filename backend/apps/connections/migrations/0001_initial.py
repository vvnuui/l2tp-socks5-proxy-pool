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
            name='Connection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('interface', models.CharField(max_length=16, verbose_name='接口名')),
                ('peer_ip', models.GenericIPAddressField(verbose_name='对端IP')),
                ('local_ip', models.GenericIPAddressField(verbose_name='本地IP')),
                ('status', models.CharField(choices=[('online', '在线'), ('offline', '离线')], default='online', max_length=16, verbose_name='状态')),
                ('connected_at', models.DateTimeField(auto_now_add=True, verbose_name='连接时间')),
                ('disconnected_at', models.DateTimeField(blank=True, null=True, verbose_name='断开时间')),
                ('bytes_sent', models.BigIntegerField(default=0, verbose_name='发送字节')),
                ('bytes_received', models.BigIntegerField(default=0, verbose_name='接收字节')),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='connections', to='accounts.l2tpaccount', verbose_name='关联账号')),
            ],
            options={
                'verbose_name': '连接',
                'verbose_name_plural': '连接',
                'db_table': 'connections',
                'ordering': ['-connected_at'],
            },
        ),
    ]
