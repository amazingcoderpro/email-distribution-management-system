from django.contrib import auth
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_jwt.serializers import jwt_encode_handler, jwt_payload_handler
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from edm import settings
from app import models
from app.serializers import personal_center
from app.permission.permission import UserPermission


class LoginView(generics.CreateAPIView):
    """登陆"""
    queryset = models.User.objects.all()
    serializer_class = personal_center.LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            username = request.data.get('username', '')
            password = request.data.get('password', '')
            code = request.data.get("code", "")
            obj = models.User.objects.filter(username=username).first()
            if obj and obj.is_active == 0:
                if code:
                    if obj.code == code:
                        obj.is_active = 1
                        obj.save()
                    else:
                        return Response({"detail": "The account is not activated, Please check the last email。"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"detail": "The account is not activated"}, status=status.HTTP_400_BAD_REQUEST)
            user = auth.authenticate(username=username, password=password)
            if not user:
                return Response({"detail": "User name password error"}, status=status.HTTP_400_BAD_REQUEST)
            if user:
                res = {}
                res["user"] = personal_center.LoginSerializer(instance=user, many=False).data
                payload = jwt_payload_handler(user)
                res["token"] = "{} {}".format(settings.JWT_AUTH_HEADER_PREFIX, jwt_encode_handler(payload))
                return Response(res, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SetPasswordView(generics.UpdateAPIView):
    """注册状态设置密码"""
    queryset = models.User.objects.all()
    serializer_class = personal_center.SetPasswordSerializer


class SetPasswordsView(generics.UpdateAPIView):
    """登陆状态设置密码"""
    queryset = models.User.objects.all()
    serializer_class = personal_center.SetPasswordsSerializer
    permission_classes = (IsAuthenticated, UserPermission)
    authentication_classes = (JSONWebTokenAuthentication,)