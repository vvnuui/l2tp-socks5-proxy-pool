"""认证视图"""

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class LoginView(APIView):
    """用户登录接口"""

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': '请输入用户名和密码'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {'detail': '用户名或密码错误'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'detail': '账号已被禁用'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'username': user.username,
            'is_superuser': user.is_superuser
        })


class LogoutView(APIView):
    """用户登出接口"""

    def post(self, request):
        if request.user.is_authenticated:
            Token.objects.filter(user=request.user).delete()

        return Response({'detail': '已登出'})


class UserInfoView(APIView):
    """获取当前用户信息"""

    def get(self, request):
        user = request.user
        return Response({
            'username': user.username,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff
        })
