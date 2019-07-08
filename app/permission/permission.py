from rest_framework.permissions import BasePermission


class UserPermission(BasePermission):

    method = ["GET", "PUT", "POST"]

    def has_object_permission(self, request, view, obj):
        if obj == request.user:
            return True
        else:
            return False