from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from io import BytesIO
import base64
from PIL import Image

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


class CustomerGroupOptView(generics.DestroyAPIView):
    """客户组编辑 删除"""
    queryset = models.CustomerGroup.objects.all()
    serializer_class = service.CustomerGroupSerializer
    permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
    authentication_classes = (JSONWebTokenAuthentication,)

    def perform_destroy(self, instance):
        instance.state = 2
        instance.save()


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


class EmailTemplate(generics.CreateAPIView):
    """邮件增加"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = service.EmailTemplateSerializer
    permission_classes = (IsAuthenticated, StorePermission)
    authentication_classes = (JSONWebTokenAuthentication,)


class UploadPicture(APIView):
    """上传图片"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def post(self, request, *args, **kwargs):

        file = request.FILES["file"]
        image = Image.open(BytesIO(file.read()))

        output_buffer = BytesIO()
        if "jp" in file._name[-4:]:
            format = "JPEG"
        image.save(output_buffer, format=format)
        byte_data = output_buffer.getvalue()
        base64_str = base64.b64encode(byte_data)
        base64_str = base64_str.decode("utf-8")

        return Response({"str": base64_str})