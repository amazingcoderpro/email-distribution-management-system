from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response

from app import models
from app.pageNumber.pageNumber import PNPagination
from app.serializers import opstores_service
from app.filters import opstores_service as opstores_service_filter
from app.permission.permission import StorePermission


class StoreInitViews(generics.CreateAPIView):
    queryset = models.Store.objects.all()
    serializer_class = opstores_service.StoreSerializer


class EmailTriggerView(generics.ListAPIView):
    """邮件 Trigger展示"""
    queryset = models.EmailTrigger.objects.all()
    serializer_class = opstores_service.EmailTriggerSerializer
    pagination_class = PNPagination
    filter_backends = (opstores_service_filter.EmailTriggerFilter,)


class EmailTriggerOptView(generics.UpdateAPIView):
    """邮件 Trigger 状态更新"""
    queryset = models.EmailTrigger.objects.all()
    serializer_class = opstores_service.EmailTriggerOptSerializer


class EmailTemplateView(generics.ListCreateAPIView):
    """邮件模版展示"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = opstores_service.EmailTemplateSerializer
    pagination_class = PNPagination
    filter_backends = (opstores_service_filter.EmailTempFilter,)


class EmailTemplateUpdateView(generics.UpdateAPIView):
    """邮件模版 更新"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = opstores_service.EmailTemplateUpdateSerializer


class EmailTemplateRetrieveView(generics.RetrieveUpdateAPIView):
    """邮件模版详情"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = opstores_service.EmailTemplateSerializer