from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
# from io import BytesIO
# import base64
# from PIL import Image
import random, string, os, json
import csv
import io

from app import models
from app.pageNumber.pageNumber import PNPagination
from app.serializers import service
from app.filters import service as service_filter
from app.permission.permission import CustomerGroupOptPermission, StorePermission
from sdk.ems import ems_api
from app.serializers import opstores_service
from task.customer_group_processor import AnalyzeCondition
from config import MYSQL_CONFIG, MONGO_CONFIG
from task.product_recommendation import ProductRecommend


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


class StoreExcelCreateView(generics.CreateAPIView):
    """店铺 Excel创建"""
    queryset = models.Store.objects.all()
    serializer_class = opstores_service.StoreSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        file = request.FILES["file"]
        reader = csv.DictReader(io.StringIO(file.read().decode('utf-8')))
        for item in reader:
            try:
                serializer = self.get_serializer(data=item)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
            except Exception:
                pass
            # headers = self.get_success_headers(serializer.data)
            # return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response({"code": 200})


class EmailTemplateView(generics.ListCreateAPIView):
    """邮件模版展示 增加"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = service.EmailTemplateSerializer
    pagination_class = PNPagination
    filter_backends = (service_filter.EmailTempFilter,)
    permission_classes = (IsAuthenticated, StorePermission)
    authentication_classes = (JSONWebTokenAuthentication,)


class EmailTemplateRetrieveView(generics.RetrieveUpdateAPIView):
    """邮件模版详情"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = service.EmailTemplateSerializer
    permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
    authentication_classes = (JSONWebTokenAuthentication,)


class TriggerEmailTemplateView(generics.CreateAPIView):
    """触发邮件模版 增加"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = service.TriggerEmailTemplateSerializer
    # pagination_class = PNPagination
    # filter_backends = (service_filter.EmailTriggerFilter,)
    permission_classes = (IsAuthenticated, StorePermission)
    authentication_classes = (JSONWebTokenAuthentication,)

#
# class EmailTemplateDeleteView(generics.DestroyAPIView):
#     """邮件模版 删除"""
#     queryset = models.EmailTemplate.objects.all()
#     serializer_class = service.EmailTemplateSerializer
#     permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
#     authentication_classes = (JSONWebTokenAuthentication,)
#
#     def perform_destroy(self, instance):
#         instance.status = 2
#         instance.save()


class EmailTemplateUpdateView(generics.UpdateAPIView):
    """邮件模版 更新"""
    queryset = models.EmailTemplate.objects.all()
    serializer_class = service.EmailTemplateUpdateSerializer
    permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
    authentication_classes = (JSONWebTokenAuthentication,)


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
        top_product = models.TopProduct.objects.filter(store=store).values("id", "top_three", "top_seven", "top_fifteen", "top_thirty").first()
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
        picture_path = "/data/nginx/edm/dist/media/"
        web_path = "https://smartsend.seamarketings.com/media/"
        # picture_path = "/Users/shaowei/"
        file = request.FILES["file"]
        store_id = models.Store.objects.filter(user=request.user).first().id
        store_path = "{}{}/".format(picture_path,store_id)
        store_web_path = "{}{}/".format(web_path,store_id)

        if not os.path.exists(store_path):
            os.makedirs(store_path)
        file_suffix = file._name[-3:]
        file_name = "{}.{}".format("".join(random.sample(string.ascii_lowercase + string.digits, 15)),file_suffix)
        file_path = "{}{}".format(store_path, file_name, )
        with open(file_path, "wb") as f:
            f.write(file.read())

        return Response({"base64_str": store_web_path + file_name})

    # def post(self, request, *args, **kwargs):
    #
    #     file = request.FILES["file"]
    #     image = Image.open(BytesIO(file.read()))
    #
    #     output_buffer = BytesIO()
    #     if "jp" in file._name[-4:]:
    #         format = "JPEG"
    #     if "png" in file._name[-4:]:
    #         format = "PNG"
    #     if "gif" in file._name[-4:]:
    #         format = "GIF"
    #     image.save(output_buffer, format=format)
    #     byte_data = output_buffer.getvalue()
    #     base64_str = base64.b64encode(byte_data)
    #     base64_str = base64_str.decode("utf-8")
    #
    #     return Response({"base64_str": base64_str})


class EmailTriggerView(generics.ListCreateAPIView):
    """邮件 Trigger展示 增加"""
    queryset = models.EmailTrigger.objects.all()
    serializer_class = service.EmailTriggerSerializer
    pagination_class = PNPagination
    filter_backends = (service_filter.EmailTriggerFilter,)
    # permission_classes = (IsAuthenticated, StorePermission)
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)


class EmailTriggerOptView(generics.UpdateAPIView):
    """邮件 Trigger 状态更新"""
    queryset = models.EmailTrigger.objects.all()
    serializer_class = service.EmailTriggerOptSerializer
    permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
    authentication_classes = (JSONWebTokenAuthentication,)


class EmailTriggerCloneView(generics.UpdateAPIView):
    """邮件 Trigger clone"""
    queryset = models.EmailTrigger.objects.all()
    serializer_class = service.EmailTriggerCloneSerializer
    permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
    authentication_classes = (JSONWebTokenAuthentication,)


class EmailTriggerEditView(generics.UpdateAPIView):
    """邮件 Trigger clone"""
    queryset = models.EmailTrigger.objects.all()
    serializer_class = service.EmailTriggerSerializer
    permission_classes = (IsAuthenticated, CustomerGroupOptPermission)
    authentication_classes = (JSONWebTokenAuthentication,)


class EmailTriggerTestEmailView(generics.CreateAPIView):
    """flow发送测试邮件"""
    permission_classes = (IsAuthenticated, StorePermission)
    authentication_classes = (JSONWebTokenAuthentication,)

    def post(self, request, *args, **kwargs):
        store = models.Store.objects.filter(user=request.user).first()
        if store.id == 1:
            return Response({"detail": "Admin store unable to send test email."}, status=status.HTTP_400_BAD_REQUEST)
        site_name = store.site_name
        # 先检测需要发送的邮箱是否正常
        customers_email_list = eval(request.data.get("customers_email_list", "[]"))
        if not customers_email_list:
            return Response({"detail": "Input email list is null."}, status=status.HTTP_400_BAD_REQUEST)
        ac = AnalyzeCondition(mysql_config=MYSQL_CONFIG, mongo_config=MONGO_CONFIG)
        customers_id_list = ac.customer_email_to_uuid_mongo(customers_email_list, site_name)
        if not customers_id_list:
            return Response({"detail": "Input email list is invalid."}, status=status.HTTP_400_BAD_REQUEST)
        elif len(customers_id_list) < len(customers_email_list):
            detail = "Part email address is valid in input email list."
        else:
            detail = "Test mail has been sent, please check it."
        #通过trigger_id和email_list去创建任务
        trigger_id = request.data.get("trigger_id")
        valid_email_list = ac.parse_trigger_tasks(trigger_id, customers_id_list, test_email=True)
        return Response({"detail": detail+"Successful email include: "+str(valid_email_list)}, status=status.HTTP_200_OK)


class SendMailView(generics.CreateAPIView):
    """邮件模版增加，测试发送邮件"""
    # queryset = models.EmailTemplate.objects.all()
    # serializer_class = service.SendMailSerializer
    permission_classes = (IsAuthenticated, StorePermission)
    authentication_classes = (JSONWebTokenAuthentication,)

    def post(self, request, *args, **kwargs):
        store = models.Store.objects.filter(user=request.user).first()
        store_url = store.domain
        email_address = request.data["email_address"]
        html = request.data["html"]
        subject = request.data["subject"]
        email_title = request.data["email_title"]
        product_condition = request.data["product_condition"]
        # html = html.replace(store_url+"?utm_source=smartsend", store_url+"?utm_source=smartsend&utm_medium=newsletter")
        # html = html.replace("*[tr_shop_name]*", store.name)
        product_list = request.data.get("product_list", None)
        if product_list:
            if product_list != "[]":
                product_list = json.loads(product_list)
                for item in product_list:
                    dic = {"email_category": "newsletter", "product_uuid": str(item["uuid"])}
                    uri_structure = "?utm_source=smartsend&utm_medium={email_category}&utm_term={product_uuid}".format(**dic)
                    new_image_url = item["url"] + uri_structure
                    html = html.replace(item["url"], new_image_url)

        # 替换 html
        pr = ProductRecommend()
        shop_info = pr.get_card_product_mongo("", store.name, email_title, "test", store_url,
                                              store.service_email, length=0, utm_medium="Newsletter")

        top_products = []
        if "top" in product_condition:
            # 获取top_products
            top_products = pr.get_top_product_by_condition(product_condition, store.id,
                                                           email_title, "test",
                                                           utm_medium="Newsletter")

        snippets_dict = pr.generate_snippets(shop_info, top_products, flow=False)
        for key, val in snippets_dict.items():
            html = html.replace("*[tr_{}]*".format(key), val)

        # store_instance = models.Store.objects.filter(user=request.user).first()
        ems_instance = ems_api.ExpertSender(store.name, store.email)

        subscribers_res = ems_instance.create_subscribers_list(store.name)
        if subscribers_res["code"] != 1:
            return Response({"detail": subscribers_res["msg"]}, status=status.HTTP_400_BAD_REQUEST)
        subscriber_flag = ems_instance.add_subscriber(subscribers_res["data"], [email_address])
        if subscriber_flag["code"] != 1:
            return Response({"detail": subscriber_flag["msg"]}, status=status.HTTP_400_BAD_REQUEST)
        result = ems_instance.create_and_send_newsletter([subscribers_res["data"]], subject, html=html)
        if result["code"] != 1:
            return Response({"detail": result["msg"]}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"status":"successful"}, status=status.HTTP_200_OK)


class TopDashboardView(generics.ListAPIView):
    """top Dashboard"""
    queryset = models.Dashboard.objects.all()
    serializer_class = service.DashboardSerializer
    # filter_backends = (service_filter.TopDashboardFilter,)
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        store = models.Store.objects.filter(user=request.user).first()
        filte_kwargs = {"store": store}
        instance = models.Dashboard.objects.filter(**filte_kwargs).order_by("-update_time").first()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class BottomDashboardView(generics.ListAPIView):
    """bottom Dashboard"""
    queryset = models.Dashboard.objects.all()
    serializer_class = service.DashboardSerializer
    filter_backends = (service_filter.TopDashboardFilter,)
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


class StoreViewList(generics.ListAPIView):
    """STORE LIST"""
    queryset = models.Store.objects.all()
    serializer_class = service.StoreSerializer
    pagination_class = PNPagination
    filter_backends = (service_filter.StoreListFilter,)
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    # def list(self, request, *args, **kwargs):
    #     queryset = self.filter_queryset(self.get_queryset())
    #     if request.query_params.get("page", ''):
    #         page = self.paginate_queryset(queryset)
    #         if page is not None:
    #             serializer = self.get_serializer(page, many=True)
    #             return self.get_paginated_response(serializer.data)
    #
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data)