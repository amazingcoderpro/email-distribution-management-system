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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if request.query_params.get("page", ''):
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)




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


class EmailTemplate(generics.ListCreateAPIView):
    """邮件模版展示 增加"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = service.EmailTemplateSerializer
    pagination_class = PNPagination
    filter_backends = (service_filter.EmailTempFilter,)
    permission_classes = (IsAuthenticated, StorePermission)
    authentication_classes = (JSONWebTokenAuthentication,)


class EmailTemplateOptView(generics.DestroyAPIView):
    """邮件模版 删除"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = service.EmailTemplateSerializer
    permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
    authentication_classes = (JSONWebTokenAuthentication,)

    def perform_destroy(self, instance):
        instance.state = 2
        instance.save()


class TopProductView(APIView):
    """Top product 展示"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def get(self, request, *args, **kwargs):
        store = models.Store.objects.filter(user=request.user).first()
        res = {
            "id": "",
            "top_three": "",
            "top_seven": "",
            "top_fifteen": "",
            "top_thirty": ""
        }
        top_product = models.TopProduct.objects.filter(store=store).values("id", "top_three", "top_seven", "top_fifteen",
                                                             "top_thirty").first()
        if not top_product:
            return Response(res)
        res["id"] = top_product["id"]
        res["top_three"] = top_product["top_three"]
        res["top_seven"] = top_product["top_seven"]
        res["top_fifteen"] = top_product["top_fifteen"]
        res["top_thirty"] = top_product["top_thirty"]
        return Response(res)


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
        if "png" in file._name[-4:]:
            format = "PNG"
        if "gif" in file._name[-4:]:
            format = "GIF"
        image.save(output_buffer, format=format)
        byte_data = output_buffer.getvalue()
        base64_str = base64.b64encode(byte_data)
        base64_str = base64_str.decode("utf-8")

        return Response({"base64_str": base64_str})


class EmailTrigger(generics.ListCreateAPIView):
    """邮件 Trigger展示 增加"""
    queryset = models.EmailTrigger.objects.all()
    serializer_class = service.EmailTriggerSerializer
    pagination_class = PNPagination
    filter_backends = (service_filter.EmailTempFilter,)
    # permission_classes = (IsAuthenticated, StorePermission)
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)


class EmailTriggerOptView(generics.DestroyAPIView):
    """邮件 Trigger 删除"""
    queryset = models.EmailTrigger.objects.all()
    serializer_class = service.EmailTemplateSerializer
    permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
    authentication_classes = (JSONWebTokenAuthentication,)

    def perform_destroy(self, instance):
        instance.state = 2
        instance.save()


class SendMail(generics.CreateAPIView):
    """邮件模版增加，测试发送邮件"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = service.SendMailSerializer
    permission_classes = (IsAuthenticated, StorePermission)
    authentication_classes = (JSONWebTokenAuthentication,)