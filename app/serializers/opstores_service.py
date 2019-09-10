from django.db import transaction
from rest_framework import serializers

from app import models

import json


class StoreSerializer(serializers.ModelSerializer):

    shopify_domain = serializers.CharField(required=True,write_only=True)
    auth_list = serializers.CharField(required=True,write_only=True)

    class Meta:
        model = models.Store
        fields = (
                  "shopify_domain",
                  "auth_list",
                  "op_user"
        )

    def validate_shopify_domain(self, data):
        if not data.endswith(".myshopify.com"):
            raise serializers.ValidationError("format error")
        return data

    def validate_auth_list(self, data):
        if not (data.startswith("[") and data.endswith("]")):
            raise serializers.ValidationError("format error")
        trigger_queryset = models.EmailTrigger.objects.filter(store_id=1, status=1).values("id")
        trigger_list = [item["id"] for item in trigger_queryset]
        auth_list = [item for item in eval(data) if item not in trigger_list]
        if auth_list:
            raise serializers.ValidationError("{} does not exist".format(auth_list))
        return data

    def create(self, validated_data):
        store_instance = models.Store.objects.filter(url=validated_data["shopify_domain"]).first()
        if validated_data.get("op_user") and store_instance:
            store_instance.op_user = validated_data["op_user"]
            store_instance.save()
        auth_list = eval(validated_data["auth_list"])
        email_trigger = models.EmailTrigger.objects.filter(store_id=1, id__in=auth_list).values("id", "title",
                                                                                                "description",
                                                                                                "relation_info",
                                                                                                "email_delay",
                                                                                                "note",
                                                                                                "status")
        with transaction.atomic():

            if not store_instance:
                # 增加用户
                user_dict = {
                    "username": validated_data["shopify_domain"],
                    "password": validated_data["shopify_domain"].lower()[:2] + "123456"
                }
                user_instance = models.User.objects.create(**user_dict)
                user_instance.set_password(user_dict["password"])
                user_instance.save()

                # 增加店铺
                store_dict = {
                    "user": user_instance,
                    "url": validated_data["shopify_domain"],
                    "init": 0,
                    "op_user": validated_data["op_user"] if validated_data.get("op_user") else "",
                }
                store_instance = super(StoreSerializer, self).create(store_dict)
                if email_trigger:
                    self.copy_trigger(email_trigger, store_instance.id)
                return store_instance
            copy_trigger_dict = models.EmailTrigger.objects.filter(store=store_instance, status__in=[0, 1], email_trigger__isnull=False).values("id","email_trigger_id","email_delay")
            copy_trigger_list = [item["email_trigger_id"] for item in copy_trigger_dict]
            del_trigger_list = [item for item in copy_trigger_list if item not in set(auth_list)]
            if del_trigger_list:
                email_trigger_list = [item for item in copy_trigger_dict if item["email_trigger_id"] in del_trigger_list]
                self.del_trigger(email_trigger_list, store_instance.id)

            add_trigger_list = [item for item in auth_list if item not in set(copy_trigger_list)]
            if add_trigger_list and email_trigger:
                email_trigger_list = [item for item in email_trigger if item["id"] in add_trigger_list]
                self.copy_trigger(email_trigger_list, store_instance.id)
            return store_instance

    def copy_trigger(self,email_trigger_list, store_id):

        for item in email_trigger_list:
            trigger_dict = {
                "store_id": store_id,
                "title": item["title"],
                "description": item["description"],
                "relation_info": item["relation_info"],
                "email_delay": item["email_delay"],
                "note": item["note"],
                "status": 1,
                "email_trigger_id": item["id"],
                "draft": 0,
            }
            trigger_instance = models.EmailTrigger.objects.create(**trigger_dict)

            email_delay = json.loads(item["email_delay"])
            for key, val in enumerate(email_delay):
                if val["type"] == "Email":
                    admin_template_instance = models.EmailTemplate.objects.filter(id=val["value"]).first()
                    template_dict = {
                        "store_id": store_id,
                        "title": admin_template_instance.title,
                        "description": admin_template_instance.description,
                        "subject": admin_template_instance.subject,
                        "logo": admin_template_instance.logo,
                        "banner": admin_template_instance.banner,
                        "heading_text": admin_template_instance.heading_text,
                        "body_text": admin_template_instance.body_text,
                        "headline": admin_template_instance.headline,
                        "html": admin_template_instance.html,
                        "customer_group_list": admin_template_instance.customer_group_list,
                        "send_rule": admin_template_instance.send_rule,
                        "send_type": admin_template_instance.send_type,
                        "product_condition": admin_template_instance.product_condition,
                        "is_cart": admin_template_instance.is_cart,
                        "product_title": admin_template_instance.product_title,
                        "banner_text": admin_template_instance.banner_text,
                        "customer_text": admin_template_instance.customer_text,
                        "email_trigger_id":trigger_instance.id
                    }
                    template_instance = models.EmailTemplate.objects.create(**template_dict)
                    val["value"] = template_instance.id
            trigger_instance.email_delay = json.dumps(email_delay)
            trigger_instance.save()


    def del_trigger(self,email_trigger_list, store_id):
        for item in email_trigger_list:
            email_delay = json.loads(item["email_delay"])
            for key, val in enumerate(email_delay):
                if val["type"] == "Email":
                    models.EmailTemplate.objects.filter(id=val["value"], store_id=store_id).update(status=2)
            models.EmailTrigger.objects.filter(id=item["id"], store_id=store_id).update(status=2)


class EmailTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailTrigger
        fields = ("id",
                  "status",     # 0--disable, 1-enable
                  "title",
                  "description",
                  "total_sents"
                  "open_rate",
                  "click_rate",
                  "revenue",
                  # "relation_info",
                  # "email_delay",
                  # "note",
                  "create_time",
                  "update_time"
        )

    # def to_representation(self, instance):
    #     data = super(EmailTriggerSerializer, self).to_representation(instance)
    #     data["open_rate"] = float(instance.open_rate)
    #     data["click_rate"] = float(instance.click_rate)
    #     data["revenue"] = float(instance.revenue)
    #     return data


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
                  "banner_text",
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