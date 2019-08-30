from rest_framework.filters import BaseFilterBackend
from app import models


class StoreFilter(BaseFilterBackend):
    """Store过滤"""

    def filter_queryset(self, request, queryset, view):
        return queryset.filter(user=request.user)


class EmailTempFilter(BaseFilterBackend):
    """邮件模版 过滤"""
    filter_keys = {
        "title": "title__icontains",
        "enable": "enable",
    }

    def filter_queryset(self, request, queryset, view):
        store = models.Store.objects.filter(name=request.query_params.get("store_name", '')).first()
        filte_kwargs = {"store":  store, "status__in": [0,1], "send_type":0}
        for filter_key in self.filter_keys.keys():
            val = request.query_params.get(filter_key, '')
            if val is not '':
                filte_kwargs[self.filter_keys[filter_key]] = val
        return queryset.filter(**filte_kwargs)


class EmailTriggerFilter(BaseFilterBackend):
    """邮件触发器 过滤"""
    # filter_keys = {
    #     "title": "title__icontains",
    #     "status": "status",
    # }

    def filter_queryset(self, request, queryset, view):
        store = models.Store.objects.filter(id=1).first()
        filte_kwargs = {"store":  store, "draft": 0, "status": 1,}
        # for filter_key in self.filter_keys.keys():
        #     val = request.query_params.get(filter_key, '')
        #     if val is not '':
        #         filte_kwargs[self.filter_keys[filter_key]] = val
        # if "status" not in filte_kwargs.keys():
        #     filte_kwargs["status__in"] =
        #print(filte_kwargs)
        return queryset.filter(**filte_kwargs)

