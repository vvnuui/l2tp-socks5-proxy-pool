# Django 后端开发规范

## 1. 代码风格
- 遵循 PEP 8 规范
- 行长度限制: 120 字符
- 使用 Black 格式化，isort 排序导入

## 2. 命名约定
| 类型 | 风格 | 示例 |
|------|------|------|
| 类名 | PascalCase | `L2TPAccount`, `ProxyConfig` |
| 函数/方法 | snake_case | `get_account_by_ip()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_CONNECTIONS` |
| 模块/文件 | snake_case | `l2tp_service.py` |

## 3. Django 模型规范
```python
class L2TPAccount(models.Model):
    """L2TP 用户账号模型"""

    class Meta:
        db_table = 'l2tp_accounts'
        ordering = ['-created_at']
        verbose_name = 'L2TP账号'

    username = models.CharField('用户名', max_length=64, unique=True)
    password = models.CharField('密码', max_length=128)
    assigned_ip = models.GenericIPAddressField('分配IP', unique=True)
    is_active = models.BooleanField('启用状态', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    def __str__(self):
        return self.username
```

## 4. DRF 序列化器规范
```python
class L2TPAccountSerializer(serializers.ModelSerializer):
    """L2TP 账号序列化器"""

    class Meta:
        model = L2TPAccount
        fields = ['id', 'username', 'assigned_ip', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_username(self, value):
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError('用户名只能包含字母、数字和下划线')
        return value
```

## 5. 服务层规范
- 业务逻辑放在 `services/` 目录
- 每个服务类负责单一职责
- 使用依赖注入便于测试

```python
# apps/network/services/gost.py
class GostService:
    """Gost 代理服务管理"""

    def __init__(self):
        self.process_manager = ProcessManager()

    def start_proxy(self, port: int, bind_ip: str) -> int:
        """启动 Socks5 代理实例

        Args:
            port: 监听端口
            bind_ip: 绑定出口 IP

        Returns:
            进程 PID

        Raises:
            GostError: 启动失败时
        """
        cmd = f'gost -L socks5://:{port} -F forward://{bind_ip}:0'
        return self.process_manager.start(cmd)
```

## 6. API 视图规范
```python
class L2TPAccountViewSet(viewsets.ModelViewSet):
    """L2TP 账号管理接口"""

    queryset = L2TPAccount.objects.all()
    serializer_class = L2TPAccountSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active']
    search_fields = ['username']
    ordering_fields = ['created_at', 'username']
```

## 7. URL 命名规范
- 使用 kebab-case: `/api/l2tp-accounts/`
- RESTful 风格: 资源名词复数
- 动作使用子路径: `/api/proxies/{id}/start/`

## 8. 异常处理
```python
from rest_framework.exceptions import APIException

class NetworkConfigError(APIException):
    status_code = 500
    default_detail = '网络配置失败'
    default_code = 'network_error'
```

## 9. 日志规范
```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.info('操作开始', extra={'user_id': user.id})
    try:
        # ...
    except Exception as e:
        logger.error('操作失败', exc_info=True)
```

## 10. 测试规范
- 测试文件命名: `test_<module>.py`
- 使用 pytest + pytest-django
- 覆盖率要求: >= 80%

```python
import pytest
from apps.accounts.models import L2TPAccount

@pytest.mark.django_db
class TestL2TPAccount:
    def test_create_account(self):
        account = L2TPAccount.objects.create(
            username='test_user',
            password='test_pass',
            assigned_ip='10.0.0.1'
        )
        assert account.username == 'test_user'
        assert account.is_active is True
```
