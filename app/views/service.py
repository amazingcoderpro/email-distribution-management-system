from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication


from app import models
from app.pageNumber.pageNumber import PNPagination
from app.serializers import service
from app.filters import service as service_filter
from app.permission.permission import CustomerGroupOptPermission, StorePermission


class CustomerGroupView(generics.ListCreateAPIView):
    """客户组列表 增加"""
    queryset = models.CustomerGroup.objects.all()
    serializer_class = service.CustomerGroupSerializer
    pagination_class = PNPagination
    filter_backends = (service_filter.CustomerGroupFilter,)
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)


class CustomerGroupOptView(generics.RetrieveUpdateDestroyAPIView):
    """客户组编辑 删除"""
    queryset = models.CustomerGroup.objects.all()
    serializer_class = service.CustomerGroupSerializer
    permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
    authentication_classes = (JSONWebTokenAuthentication,)


class StoreView(generics.ListAPIView):
    """店铺 展示"""
    queryset = models.Store.objects.all()
    serializer_class = service.StoreSerializer
    filter_backends = (service_filter.StoreFilter,)
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)


class StoreOperView(generics.UpdateAPIView):
    """店铺 改 删"""
    queryset = models.Store.objects.all()
    serializer_class = service.StoreSerializer
    permission_classes = (IsAuthenticated, StorePermission)
    authentication_classes = (JSONWebTokenAuthentication,)