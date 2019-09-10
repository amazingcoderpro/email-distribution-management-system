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
    # pagination_class = PNPagination
    filter_backends = (opstores_service_filter.EmailTriggerFilter,)

    def list(self, request, *args, **kwargs):
        url = request.query_params.get("shopify_domain", "")
        if not url:
            return Response({
                        "shopify_domain": [
                            "This field is required."
                        ]
                    }, status=400)
        store = models.Store.objects.filter(url=url).first()
        query_trigger = models.EmailTrigger.objects.filter(store=store, status__in=[0, 1]).values("email_trigger_id",
                                                                                                  "status",
                                                                                                  "total_sents",
                                                                                                  "open_rate",
                                                                                                  "click_rate",
                                                                                                  "revenue")
        user_triggers = {}
        if query_trigger:
            for item in query_trigger:
                if item["email_trigger_id"]:
                    user_triggers[item["email_trigger_id"]] = {"status": item['status'],
                                                               "total_sents": item["total_sents"],
                                                               "open_rate": item['open_rate'],
                                                               "click_rate": item['click_rate'],
                                                               "revenue": item['revenue']
                                                               }
            # query_trigger_ids = [item["email_trigger_id"] for item in query_trigger]

        #print("###", query_trigger)
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        response = serializer.data
        for item in response:
            if item["id"] not in user_triggers.keys():
                item["is_auth"] = 0
            else:
                item["is_auth"] = 1
                trg = user_triggers.get(item['id'], {})
                item['status'] = trg.get("status", 1)
                item['total_sents'] = trg.get("total_sents", 0)
                item['open_rate'] = float(trg.get("open_rate", 0))
                item['click_rate'] = float(trg.get("click_rate", 0))
                item['revenue'] = float(trg.get("revenue", 0))
        return Response(response)


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