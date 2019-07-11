from rest_framework.permissions import BasePermission
from app import models


class UserPermission(BasePermission):

    method = ["GET", "PUT", "POST"]

    def has_object_permission(self, request, view, obj):
        if obj == request.user:
            return True
        else:
            return False


class CustomerGroupOptPermission(BasePermission):

    def has_object_permission(self, request, view, obj):
        if obj.store == models.Store.objects.filter(user=request.user).first():
            return True
        else:
            return False


class StorePermission(BasePermission):

    def has_object_permission(self, request, view, obj):
            if obj.user == request.user:
                return True
            return False