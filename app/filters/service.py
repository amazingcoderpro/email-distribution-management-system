from rest_framework.filters import BaseFilterBackend
from app import models


class CustomerGroupFilter(BaseFilterBackend):
    """客户列表过滤"""

    filter_keys = {
        "title": "title__iregex",
    }

    def filter_queryset(self, request, queryset, view):
        store = models.Store.objects.filter(user=request.user).first()
        filte_kwargs = {"store":  store, "state__in" : [0,1]}
        for filter_key in self.filter_keys.keys():
            val = request.query_params.get(filter_key, '')
            if val is not '':
                if filter_key == "title":
                    filte_kwargs[self.filter_keys[filter_key]] = ".*" + val.replace(" ", ".*") + ".*"
                    continue
                filte_kwargs[self.filter_keys[filter_key]] = val
        return queryset.filter(**filte_kwargs)


class StoreFilter(BaseFilterBackend):
    """Store过滤"""

    def filter_queryset(self, request, queryset, view):
        return queryset.filter(user=request.user)


class EmailTempFilter(BaseFilterBackend):
    """邮件模版 过滤"""

    def filter_queryset(self, request, queryset, view):
        store = models.Store.objects.filter(user=request.user).first()
        filte_kwargs = {"store":  store, "state__in": [0,1]}
        return queryset.filter(**filte_kwargs)


class EmailTriggerFilter(BaseFilterBackend):
    """邮件触发器 过滤"""

    def filter_queryset(self, request, queryset, view):
        store = models.Store.objects.filter(user=request.user).first()
        filte_kwargs = {"store":  store, "type__in": [0,1]}
        return queryset.filter(**filte_kwargs)


class TopDashboardFilter(BaseFilterBackend):
    """Dashboard 过滤"""
    filter_keys = {
        "begin_time": "create_time__gte",
        "end_time": "create_time__lte",
    }

    def filter_queryset(self, request, queryset, view):
        store = models.Store.objects.filter(user=request.user).first()
        filte_kwargs = {"store":  store}
        for filter_key in self.filter_keys.keys():
            val = request.query_params.get(filter_key, '')
            if val is not '':
                filte_kwargs[self.filter_keys[filter_key]] = val
        return queryset.filter(**filte_kwargs)
