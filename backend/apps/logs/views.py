"""系统日志视图"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import SystemLog
from .serializers import SystemLogSerializer


class SystemLogViewSet(viewsets.ReadOnlyModelViewSet):
    """系统日志查看接口"""

    queryset = SystemLog.objects.all()
    serializer_class = SystemLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['level', 'log_type', 'account']
    search_fields = ['message', 'interface']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return super().get_queryset().select_related('account')

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """获取最近日志"""
        limit = int(request.query_params.get('limit', 50))
        limit = min(limit, 200)

        logs = self.get_queryset()[:limit]
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def errors(self, request):
        """获取错误日志"""
        limit = int(request.query_params.get('limit', 50))
        logs = self.get_queryset().filter(level='error')[:limit]
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """按类型分组统计"""
        from django.db.models import Count

        stats = SystemLog.objects.values('log_type').annotate(count=Count('id'))
        return Response(list(stats))

    @action(detail=False, methods=['delete'])
    def clear_old(self, request):
        """清理旧日志"""
        from datetime import timedelta

        from django.utils import timezone

        days = int(request.query_params.get('days', 30))
        cutoff = timezone.now() - timedelta(days=days)

        deleted, _ = SystemLog.objects.filter(created_at__lt=cutoff).delete()
        return Response({'deleted': deleted})
