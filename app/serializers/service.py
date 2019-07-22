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
                  "customer_shop",
                  "sender_address",
                  "timezone",
                  "update_time",
                  "store_view_id")
        extra_kwargs = {
            'name': {'write_only': False, 'read_only': True},
            'url': {'write_only': False, 'read_only': True},
            'email': {'write_only': False, 'read_only': True},
        }


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailTemplate
        fields = ("id",
                  "title",
                  "description",
                  "subject",
                  "heading_text",
                  "logo",
                  "banner",
                  "headline",
                  "body_text",
                  "product_list",
                  "send_rule",
                  "customer_group_list",
                  "state",
                  # "send_type",
                  "create_time",
                  "update_time"
        )

    def create(self, validated_data):
        validated_data["store"] = models.Store.objects.filter(user=self.context["request"].user).first()
        instance = super(EmailTemplateSerializer, self).create(validated_data)
        return instance


class EmailTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailTrigger
        fields = ("id",
                  "title",
                  "description",
                  "open_rate",
                  "click_rate",
                  "click_rate",
                  "members",
                  "trigger_info",
                  "email_delay",
                  "create_time",
                  "update_time"
        )

    def create(self, validated_data):
        validated_data["store"] = models.Store.objects.filter(user=self.context["request"].user).first()
        instance = super(EmailTriggerSerializer, self).create(validated_data)
        return instance


class SendMailSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailTemplate
        fields = ("id",
                  "title",
                  "description",
                  "subject",
                  "heading_text",
                  "logo",
                  "banner",
                  "headline",
                  "body_text",
                  "product_list",
                  "state",
                  # "send_type",
                  "create_time",
                  "update_time",
        )

    def create(self, validated_data):
        print(self.context["request"].data["email_address"])
        validated_data["store"] = models.Store.objects.filter(user=self.context["request"].user).first()
        validated_data["send_type"] = 3
        validated_data["state"] = 1
        instance = super(SendMailSerializer, self).create(validated_data)
        return instance