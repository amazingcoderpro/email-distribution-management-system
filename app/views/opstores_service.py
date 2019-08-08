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




# class EmailTemplateView(generics.ListCreateAPIView):
#     """邮件模版展示 增加"""
#     queryset = models.EmailTemplate.objects.all()
#     serializer_class = service.EmailTemplateSerializer
#     pagination_class = PNPagination
#     filter_backends = (service_filter.EmailTempFilter,)
#     permission_classes = (IsAuthenticated, StorePermission)
#     authentication_classes = (JSONWebTokenAuthentication,)


class EmailTriggerView(generics.ListAPIView):
    """邮件 Trigger展示"""
    queryset = models.EmailTrigger.objects.all()
    serializer_class = opstores_service.EmailTriggerSerializer
    pagination_class = PNPagination
    filter_backends = (opstores_service_filter.EmailTriggerFilter,)
