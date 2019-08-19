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
                  "service_email",
                  "sender",
                  "domain",
                  "logo",
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
                  "banner_text",
                  "headline",
                  "body_text",
                  "product_list",
                  "product_condition",
                  "send_rule",
                  "customer_group_list",
                  "product_title",
                  "status",
                  "enable",
                  "product_title",
                  "html",
                  # "send_type",
                  "revenue",
                  "create_time",
                  "update_time",
                  "is_cart"
        )

    def create(self, validated_data):
        store = models.Store.objects.filter(user=self.context["request"].user).first()
        validated_data["store"] = store
        instance = super(EmailTemplateSerializer, self).create(validated_data)
        html = validated_data["html"]
        store_url = store.domain
        html = html.replace(store_url+"?utm_source=smartsend", store_url+f"?utm_source=smartsend&utm_medium=newsletter&utm_campaign={instance.title}&utm_term={instance.id}")

        product_list = validated_data.get("product_list", None)
        if product_list:
            if product_list != "[]":
                try:
                    product_list = json.loads(validated_data["product_list"])
                    for item in product_list:
                        dic = {"email_category": "newsletter", "template_name": instance.title, "product_uuid_template_id": str(item["uuid"]) + "_" + str(instance.id)}
                        uri_structure = "?utm_source=smartsend&utm_medium={email_category}&utm_campaign={template_name}&utm_term={product_uuid_template_id}".format(**dic)
                        new_iamge_url = item["url"] + uri_structure
                        html = html.replace(item["url"], new_iamge_url)
                except Exception as e:
                    raise serializers.ValidationError("Param 'product_list' must be a json format")
                instance.html = html
                instance.save()
        return instance

    def to_representation(self, instance):
        data = super(EmailTemplateSerializer, self).to_representation(instance)
        records = models.EmailRecord.objects.filter(email_template_id=instance.id, store_id=instance.store.id).all()
        sents = clicks = opens = 0
        if records:
            for r in records:
                sents += r.sents if isinstance(r.sents, int) else 0
                clicks += r.clicks if isinstance(r.clicks, int) else 0
                opens += r.opens if isinstance(r.opens, int) else 0

        data["revenue"] = float(data["revenue"])
        data["click_rate"] = 0
        data["open_rate"] = 0
        if sents > 0:
            data["click_rate"] = clicks/sents
            data["open_rate"] = opens/sents

        return data


class EmailTemplateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailTemplate
        fields = (
                "enable",
                "status",
        )

    def update(self, instance, validated_data):
        if instance.status == 2:
            return instance

        instance = super(EmailTemplateUpdateSerializer, self).update(instance, validated_data)
        if "enable" in validated_data.keys():
            # 如果是禁用或启用，则将task中状态为待发送和已禁用的同步修改成禁用或待发送
            models.EmailTask.objects.filter(template_id=instance.id, status__in=[0, 3]).update(status=(0 if instance.enable==1 else 3))
        else:
            # 如果是删除模板，则将对应的task中状态为待发送和已禁用的，改成删除状态
            models.EmailTask.objects.filter(template_id=instance.id, status__in=[0, 3]).update(status=4)
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
                  "banner_text",
                  "headline",
                  "body_text",
                  "product_list",
                  "product_condition",
                  "send_rule",
                  "product_title",
                  "customer_group_list",
                  "status",
                  "html",
                  # "send_type",
                  "create_time",
                  "update_time",
                  "is_cart"
        )

    def create(self, validated_data):
        store = models.Store.objects.filter(user=self.context["request"].user).first()
        validated_data["store"] = store
        validated_data["status"] = 0    # 默认为禁用状态
        validated_data["send_type"] = 1
        instance = super(TriggerEmailTemplateSerializer, self).create(validated_data)
        html = validated_data["html"]
        store_url = store.domain
        html = html.replace(store_url+"?utm_source=smartsend", store_url+f"?utm_source=smartsend&utm_medium=flow&utm_capaign={instance.subject}&utm_term={instance.id}")
        html = html.replace("*[tr_shop_name]*", store.name)
        product_list = validated_data.get("product_list", None)
        if product_list:
            if product_list != "[]":
                try:
                    product_list = json.loads(validated_data["product_list"])
                    for item in product_list:
                        dic = {"email_category": "flow", "template_name": instance.subject,
                               "product_uuid_template_id": str(item["uuid"]) + "_" + str(instance.id)}
                        uri_structure = "?utm_source=smartsend&utm_medium={email_category}&utm_campaign={template_name}&utm_term={product_uuid_template_id}".format(
                            **dic)
                        new_iamge_url = item["url"] + uri_structure
                        html = html.replace(item["url"], new_iamge_url)
                except Exception as e:
                    raise serializers.ValidationError("Param 'product_list' must be a json format")
                instance.html = html
                instance.save()
        return instance


class EmailTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailTrigger
        fields = ("id",
                  "status",     # 0--disable, 1-enable
                  "title",
                  "description",
                  "open_rate",
                  "click_rate",
                  "revenue",
                  "relation_info",
                  "email_delay",
                  "note",
                  "create_time",
                  "update_time"
        )

    def create(self, validated_data):
        validated_data["store"] = models.Store.objects.filter(user=self.context["request"].user).first()
        instance = super(EmailTriggerSerializer, self).create(validated_data)
        return instance

    def to_representation(self, instance):
        data = super(EmailTriggerSerializer, self).to_representation(instance)
        data["open_rate"] = float(instance.open_rate)
        data["click_rate"] = float(instance.click_rate)
        data["revenue"] = float(instance.revenue)
        return data


class EmailTriggerOptSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailTrigger
        fields = (
            "status",     # 0--disable, 1-enable
        )

    def update(self, instance, validated_data):
        if instance.status == 2:
            return instance

        task_status = 0
        if validated_data["status"] == 0:
            task_status = 3
        elif validated_data["status"] == 1:
            task_status = 0
        elif validated_data["status"] == 2:
            task_status = 4
        else:
            raise serializers.ValidationError("Trigger status must be in options [0, 1, 2]")

        validated_data["draft"] = 0
        instance = super(EmailTriggerOptSerializer, self).update(instance, validated_data)
        models.EmailTask.objects.filter(email_trigger_id=instance.id, status__in=[0, 3]).update(status=task_status)
        return instance


class EmailTriggerCloneSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailTrigger
        fields = (
            "id",
            "status",     # 0--disable, 1-enable
        )

    def update(self, instance, validated_data):
        store = models.Store.objects.filter(user=self.context["request"].user).first()
        email_delay = json.loads(instance.email_delay)
        for key, val in enumerate(email_delay):
            if val["type"] == "Email":
                email_template = models.EmailTemplate.objects.filter(id=val["value"]).values("id",
                                                                                               "title",
                                                                                               "description",
                                                                                               "subject",
                                                                                               "heading_text",
                                                                                               "headline",
                                                                                               "body_text",
                                                                                               "customer_group_list",
                                                                                               "html",
                                                                                               "send_rule",
                                                                                               "send_type",
                                                                                               "product_condition",
                                                                                                "enable",
                                                                                             "logo",
                                                                                             "banner",
                                                                                             "is_cart",
                                                                                             "product_title",
                                                                                             "banner_text"
                                                                                             ).first()
                template_dict = {
                    "store": store,
                    "title": email_template["title"],
                    "description": email_template["description"],
                    "subject": email_template["subject"],
                    "heading_text": email_template["heading_text"],
                    "body_text": email_template["body_text"],
                    "headline": email_template["headline"],
                    "html": email_template["html"],
                    "customer_group_list": email_template["customer_group_list"],
                    "send_rule": email_template["send_rule"],
                    "send_type": email_template["send_type"],
                    "product_condition": email_template["product_condition"],
                    "enable": email_template["enable"],
                    "logo": email_template["logo"],
                    "banner": email_template["banner"],
                    "is_cart": email_template["is_cart"],
                    "product_title": email_template["product_title"],
                    "banner_text": email_template["banner_text"]
                }
                emailtemplate_instance = models.EmailTemplate.objects.create(**template_dict)
                val["value"] = emailtemplate_instance.id

        dic = {
            "store": store,
            "title": instance.title,
            "description": instance.description,
            "relation_info": instance.relation_info,
            "email_delay": json.dumps(email_delay),
            "note": instance.note,
            "status": instance.status,
            # "status": 0,    #新克隆出来的模板，状态应该是0,默认是禁用状态
            "is_open": instance.is_open,
            "draft": 1
        }

        clone_instance = models.EmailTrigger.objects.create(**dic)
        return clone_instance

    def to_representation(self, instance):
        data = super(EmailTriggerCloneSerializer, self).to_representation(instance)
        data["title"] = instance.title
        data["description"] = instance.description
        data["relation_info"] = instance.relation_info
        data["email_delay"] = instance.email_delay
        data["note"] = instance.note
        return data



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
        validated_data["status"] = 0
        validated_data["enable"] = 0
        instance = super(SendMailSerializer, self).create(validated_data)

        ems_instance = ems_api.ExpertSender(store_instance.name, store_instance.email)

        subscribers_res = ems_instance.create_subscribers_list(store_instance.name)
        if subscribers_res["code"] != 1:
            raise serializers.ValidationError(subscribers_res["msg"])
        subscriber_flag = ems_instance.add_subscriber(subscribers_res["data"],email_address)
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