from rest_framework import serializers
from app import models


class CustomerGroupSerializer(serializers.ModelSerializer):
    """客户组列表增加"""
    # username = serializers.CharField(required=True)
    # password = serializers.CharField(required=True, min_length=5, write_only=True)

    class Meta:
        model = models.CustomerGroup
        # depth = 1
        fields = ("id", "title", "description", "open_rate", "click_rate", "members", "relation_info", "create_time", "update_time")
        # extra_kwargs = {
        #     'password': {'write_only': True},
        #     'email': {'read_only': True}
        # }

    def create(self, validated_data):
        validated_data["store"] = models.Store.objects.filter(user=self.context["request"].user).first()
        instance = super(CustomerGroupSerializer, self).create(validated_data)
        return instance


class StoreSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Store
        fields = ("id",
                  "name",
                  "url",
                  "email",
                  "sender",
                  "letter_domain",
                  "news_domain",
                  "message_domain",
                  "customer_shop",
                  "customer_email",
                  "timezone",
                  "update_time",
                  "store_view_id")
        extra_kwargs = {
            'name': {'write_only': False, 'read_only': True},
            'url': {'write_only': False, 'read_only': True},
            'email': {'write_only': False, 'read_only': True},
            'timezone': {'write_only': False, 'read_only': True},
            # 'country': {'write_only': False, 'read_only': True},
            # 'city': {'write_only': False, 'read_only': True},

            # 'store_view_id': {'write_only': True, 'read_only': True},
        }

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super(StoreSerializer, self).create(validated_data)

    # def to_representation(self, instance):
    #     data = super(StoreSerializer, self).to_representation(instance)
    #     data["url_format"] = "https://" + instance.url + SHOPIFY_CONFIG["utm_format"]
    #     return data