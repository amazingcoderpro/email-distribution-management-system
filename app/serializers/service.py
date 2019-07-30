from rest_framework import serializers
from app import models
from sdk.ems import ems_api
import json


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
                  "domain",
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
                  "html",
                  # "send_type",
                  "create_time",
                  "update_time"
        )

    def create(self, validated_data):
        store = models.Store.objects.filter(user=self.context["request"].user).first()
        validated_data["store"] = store
        instance = super(EmailTemplateSerializer, self).create(validated_data)
        html = validated_data["html"]

        product_list = json.loads(validated_data["product_list"])
        for item in product_list:
            dic = {"email_category": "newsletter", "template_name": instance.title, "product_uuid_template_id": str(item["uuid"]) + "_" + str(instance.id)}
            uri_structure = "?utm_source=smartsend&utm_medium={email_category}&utm_campaign={template_name}&utm_term={product_uuid_template_id}".format(**dic)
            new_iamge_url = item["url"] + uri_structure
            html = html.replace(item["url"], new_iamge_url)
        instance.html = html
        instance.save()
        return instance


class TriggerEmailTemplateSerializer(serializers.ModelSerializer):
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
                  "html",
                  # "send_type",
                  "create_time",
                  "update_time"
        )

    def create(self, validated_data):
        store = models.Store.objects.filter(user=self.context["request"].user).first()
        validated_data["store"] = store
        validated_data["state"] = 1
        validated_data["send_type"] = 1
        instance = super(TriggerEmailTemplateSerializer, self).create(validated_data)
        html = validated_data["html"]

        product_list = json.loads(validated_data["product_list"])
        for item in product_list:
            dic = {"email_category": "newsletter", "template_name": instance.title, "product_uuid_template_id": str(item["uuid"]) + "_" + str(instance.id)}
            uri_structure = "?utm_source=smartsend&utm_medium={email_category}&utm_campaign={template_name}&utm_term={product_uuid_template_id}".format(**dic)
            new_iamge_url = item["url"] + uri_structure
            html = html.replace(item["url"], new_iamge_url)
        instance.html = html
        instance.save()
        # ems_instance = ems_api.ExpertSender(store.name, store.email)
        # result = ems_instance.create_transactional_message(instance.subject, html=instance.html,)
        # if result["code"] != 1:
        #     raise serializers.ValidationError(result["msg"])
        # models.EmailRecord.objects.create(uuid=result["data"],email_template_id=instance.id,type=1,email_trigger_id)
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
                  "relation_info",
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
        fields = (
                  # "id",
                  # "title",
                  # "description",
                  "subject",
                  # "heading_text",
                  # "logo",
                  # "banner",
                  # "headline",
                  # "body_text",
                  # "product_list",
                  # "state",
                  # # "send_type",
                  # "create_time",
                  # "update_time",
        )

    def create(self, validated_data):
        email_address = [self.context["request"].data["email_address"]]
        html = [self.context["request"].data["html"]]
        store_instance = models.Store.objects.filter(user=self.context["request"].user).first()
        validated_data["store"] = store_instance
        validated_data["send_type"] = 3
        validated_data["state"] = 0
        instance = super(SendMailSerializer, self).create(validated_data)

        ems_instance = ems_api.ExpertSender(store_instance.name, store_instance.email)

        subscribers_res = ems_instance.create_subscribers_list(store_instance.name)
        if subscribers_res["code"] != 1:
            raise serializers.ValidationError(subscribers_res["msg"])
        subscriber_flag =  ems_instance.add_subscriber(subscribers_res["data"],email_address)
        if subscriber_flag["code"] != 1:
            raise serializers.ValidationError(subscriber_flag["msg"])
        result = ems_instance.create_and_send_newsletter([subscribers_res["data"]], store_instance.name, "https://smartsend.seamarketings.com/EmailPage?id={}".format(instance.id))
        if result["code"] != 1:
            raise serializers.ValidationError(result["msg"])
        return instance


class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Dashboard
        fields = (
            "revenue",
            "orders",
            "total_open",
            "total_click",
            "total_sent",

            "total_revenue",
            "total_orders",
            "avg_repeat_purchase_rate",
            "avg_conversion_rate",
            "total_sent",
            "avg_open_rate",
            "avg_click_rate",
            "avg_unsubscribe_rate",
            "create_time",
            "update_time",
        )