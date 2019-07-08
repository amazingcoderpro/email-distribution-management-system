from rest_framework import serializers
from app import models


class LoginSerializer(serializers.ModelSerializer):
    """登录"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, min_length=5, write_only=True)

    class Meta:
        model = models.User
        depth = 1
        fields = ("id", "username", "password", "first_name", "last_name", "email")
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'read_only': True}
        }


class SetPasswordSerializer(serializers.ModelSerializer):
    """shopify设置密码"""
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = models.User
        fields = ("id", "username", "password", "password2", "create_time", "email")
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'read_only': True, },
        }

    def validate(self, attrs):
        if not attrs["password"] == attrs["password2"]:
            raise serializers.ValidationError("Two passwords are inconsistent, please re-enter")
        del attrs["password2"]
        return attrs

    def update(self, instance, validated_data):
        if instance.username == validated_data["username"] and instance.is_active == 1:
            raise serializers.ValidationError("Please check that the input or account is activated.")
        instance.is_active = 1
        instance.set_password(validated_data["password"])
        instance.save()
        # comment = {"username": instance.username, "password": validated_data["password"], "code": instance.code}
        # # msg = send_sms_agent.SMS(content=comment, to=(instance.email,))
        # msg = send_sms_agent.SMS(content=comment, to=(instance.email,))
        # msg.send_email()
        return instance


class SetPasswordsSerializer(serializers.ModelSerializer):
    """用户删 改 查"""
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = models.User
        fields = ("id", "password", "password2",)
        extra_kwargs = {
            'username': { 'read_only': True},
            'password': {'write_only': True, 'read_only': False},
        }

    def validate(self, attrs):
        if not attrs["password"] == attrs["password2"]:
            raise serializers.ValidationError("Two passwords are inconsistent, please re-enter")
        del attrs["password2"]
        return attrs

    def update(self, instance, validated_data):
        user = super(SetPasswordsSerializer, self).update(instance, validated_data=validated_data)
        user.set_password(validated_data["password"])
        user.save()
        return instance