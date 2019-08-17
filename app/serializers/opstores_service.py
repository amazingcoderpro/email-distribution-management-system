from django.db import transaction
from rest_framework import serializers

from app import models

import json


class StoreSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, )
    domain = serializers.CharField(required=True, )
    url = serializers.CharField(required=True,)
    password = serializers.CharField(required=True,write_only=True)
    timezone = serializers.CharField(required=True)

    class Meta:
        model = models.Store
        fields = (
                  "name",
                  "domain",
                  "url",
                  "email",
                  "service_email",
                  "logo",
                  "sender",
                  "sender_address",
                  "store_view_id",
                  "timezone",
                  "password"
        )
        extra_kwargs = {
            'name': {'read_only': True},
            'domain': {'read_only': True},
            'url': {'read_only': True},
        }

    def create(self, validated_data):
        store_name = models.Store.objects.filter(name=validated_data["name"]).first()
        store_domain = models.Store.objects.filter(name=validated_data["domain"]).first()
        store_url = models.Store.objects.filter(name=validated_data["url"]).first()
        if store_name:
            return store_name
        elif store_domain:
            return store_domain
        elif store_url:
            return store_url
        with transaction.atomic():
            # 增加用户
            user_dict = {}
            user_dict["username"] = validated_data["url"]
            user_dict["password"] = self.context["request"].data["password"]
            user_dict["email"] = validated_data.get("email") if validated_data.get("email") else ""
            user_instance = models.User.objects.create(**user_dict)
            user_instance.set_password(user_dict["password"])
            user_instance.save()
            # 增加店铺
            store_dict = {}
            store_dict["user"] = user_instance
            store_dict["name"] = validated_data["name"]
            store_dict["email"] = validated_data.get("email") if validated_data.get("email") else ""
            store_dict["url"] = validated_data["url"]
            store_dict["logo"] = validated_data.get("logo") if validated_data.get("logo") else ""
            store_dict["service_email"] = validated_data.get("service_email") if validated_data.get("service_email") else "service@{shop_name}.com".format(shop_name=validated_data["name"].lower())
            store_dict["timezone"] = validated_data["timezone"]
            store_dict["domain"] = validated_data["domain"]
            store_dict["user"] = user_instance
            store_dict["sender"] = validated_data["sender"] if validated_data.get("sender") else validated_data["name"]
            store_dict["sender_address"] = validated_data["sender_address"] if validated_data.get("sender_address") else "noreply@letter.{shop_name}.com".format(shop_name=validated_data["name"].lower())
            store_dict["store_view_id"] = validated_data["store_view_id"] if validated_data.get("store_view_id") else ""
            store_dict["init"] = 0
            instance = super(StoreSerializer, self).create(store_dict)

            template_record = {}
            customer_group = models.CustomerGroup.objects.filter(store_id=1, state__in=[0, 1]).values("id", "title", "description", "relation_info")
            for item in customer_group:
                trigger_dict = {
                    "store": instance,
                    "title": item["title"],
                    "description": item["description"],
                    "relation_info": item["relation_info"],
                    "state": 0
                }
                customer_instance = models.CustomerGroup.objects.create(**trigger_dict)
                template_record[item["id"]] = customer_instance.id

            email_template = models.EmailTemplate.objects.filter(store_id=1, status__in=[0, 1]).values("id", "title", "description", "subject", "logo", "banner",
                                                                                    "heading_text", "headline",
                                                                                    "body_text", "customer_group_list",
                                                                                    "html", "send_rule", "send_type","product_condition", "is_cart", "product_title")

            email_template_record = {}
            for item in email_template:
                customer_group_list = eval(item["customer_group_list"])
                for key, val in enumerate(customer_group_list):
                    customer_group_list[key] = template_record[val]
                template_dict = {
                    "store": instance,
                    "title": item["title"],
                    "description": item["description"],
                    "subject": item["subject"],
                    "logo": item["logo"],
                    "banner": item["banner"],
                    "heading_text": item["heading_text"],
                    "body_text": item["body_text"],
                    "headline": item["headline"],
                    "html": item["html"],
                    "customer_group_list": customer_group_list,
                    "send_rule": item["send_rule"],
                    "send_type": item["send_type"],
                    "product_condition": item["product_condition"],
                    "is_cart": item["is_cart"],
                    "product_title": item["product_title"]
                }
                emailtemplate_instance = models.EmailTemplate.objects.create(**template_dict)
                email_template_record[item["id"]] = emailtemplate_instance.id

            email_trigger = models.EmailTrigger.objects.filter(store_id=1, draft=0, status__in=[0, 1]).values("title", "description","relation_info","email_delay","is_open", "note", "status")
            for item in email_trigger:
                email_delay = json.loads(item["email_delay"])
                for key, val in enumerate(email_delay):
                    if val["type"] == "Email":
                        val["value"] = email_template_record[val["value"]]

                trigger_dict = {"store": instance, "title": item["title"], "description": item["description"], "relation_info": item["relation_info"], "email_delay": json.dumps(email_delay), "is_open": item["is_open"], "note": item["note"], "status": item["status"]}
                models.EmailTrigger.objects.create(**trigger_dict)

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

        instance = super(EmailTriggerOptSerializer, self).update(instance, validated_data)
        models.EmailTask.objects.filter(email_trigger_id=instance.id, status__in=[0, 3]).update(status=task_status)
        return instance


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
                  "status",
                  "enable",
                  "html",
                  # "send_type",
                  "revenue",
                  "create_time",
                  "update_time",
        )

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