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
        print(queryset.filter(**filte_kwargs))
        return queryset.filter(**filte_kwargs)


class StoreListFilter(BaseFilterBackend):
    """StoreList过滤"""
    filter_keys = {
        "name": "name__iregex",
    }

    def filter_queryset(self, request, queryset, view):
        # store = models.Store.objects.filter(user=request.user).first()
        filte_kwargs = {}
        for filter_key in self.filter_keys.keys():
            val = request.query_params.get(filter_key, '')
            if val is not '':
                # if filter_key == "name":
                #     filte_kwargs[self.filter_keys[filter_key]] = ".*" + val.replace(" ", ".*") + ".*"
                #     continue
                filte_kwargs[self.filter_keys[filter_key]] = val
        print(filte_kwargs)
        return queryset.filter(**filte_kwargs)


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
        store = models.Store.objects.filter(user=request.user).first()
        filte_kwargs = {"store":  store, "status__in": [0,1], "send_type":0}
        for filter_key in self.filter_keys.keys():
            val = request.query_params.get(filter_key, '')
            if val is not '':
                filte_kwargs[self.filter_keys[filter_key]] = val
        return queryset.filter(**filte_kwargs)


class EmailTriggerFilter(BaseFilterBackend):
    """邮件触发器 过滤"""
    filter_keys = {
        "title": "title__icontains",
        "status": "status",
    }

    def filter_queryset(self, request, queryset, view):
        store = models.Store.objects.filter(user=request.user).first()
        filte_kwargs = {"store":  store, "draft": 0}
        for filter_key in self.filter_keys.keys():
            val = request.query_params.get(filter_key, '')
            if val is not '':
                filte_kwargs[self.filter_keys[filter_key]] = val
        if "status" not in filte_kwargs.keys():
            filte_kwargs["status__in"] = [0, 1]
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
