from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
# from django_hstore import hstore
from django_mysql.models import JSONField


class User(AbstractUser):
    """系统用户表"""
    username = models.CharField(max_length=255, unique=True, verbose_name="账户")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="账户邮箱")
    password = models.CharField(max_length=128, blank=True, null=True,  verbose_name="密码")
    code = models.CharField(max_length=255, blank=True, null=True, unique=True, verbose_name="用户唯一标识")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'user'


class Store(models.Model):
    """店铺表"""
    name = models.CharField(blank=True, null=True, max_length=255, verbose_name="店铺名称")
    url = models.CharField(db_index=True, blank=True, null=False, max_length=255, unique=True, verbose_name="店铺URL")
    domain = models.CharField(blank=True, null=True, max_length=255, unique=True, verbose_name="店铺domain")
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        blank=True,
    )
    token = models.CharField(blank=True, null=True, max_length=255, verbose_name="账号使用标识")
    hmac = models.CharField(blank=True, null=True, max_length=255, verbose_name="hmac")
    timezone = models.CharField(blank=True, null=True, max_length=255, verbose_name="店铺的时区")
    # shop_alias = models.CharField(blank=True, null=True, max_length=255, verbose_name="your shop")
    sender = models.CharField(blank=True, null=True, max_length=255, verbose_name="sender")
    # letter_domain = models.CharField(blank=True, null=True, max_length=255, verbose_name="letter_domain")
    # news_domain = models.CharField(blank=True, null=True, max_length=255, verbose_name="news_domain")
    # message_domain = models.CharField(blank=True, null=True, max_length=255, verbose_name="message_domain")
    customer_shop = models.CharField(blank=True, null=True, max_length=255, verbose_name="customer_shop")
    sender_address = models.CharField(blank=True, null=True, max_length=255, verbose_name="customer_email")
    store_view_id = models.CharField(blank=True, null=True, max_length=100, verbose_name=u"店铺的GA中的view id")
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING, blank=True, null=True, unique=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'store'


class Dashboard(models.Model):
    """Dashboard"""
    revenue = models.FloatField(default=0, verbose_name="Revenue")
    orders = models.IntegerField(default=0, verbose_name="Orders")
    repeat_purchase_rate = models.FloatField(blank=True, null=True,  verbose_name="Repeat Purchase Rate")
    conversion_rate = models.FloatField(blank=True, null=True,   verbose_name="Conversion Rate")
    sent = models.IntegerField(blank=True, null=True,  verbose_name="Sent")
    open_rate = models.FloatField(blank=True, null=True,  verbose_name="Open Rate")
    click_rate = models.FloatField(blank=True, null=True,  verbose_name="Click Rate")
    unsubscribe_rate = models.FloatField(blank=True, null=True,  verbose_name="Unsubscribe Rate")
    total_revenue = models.FloatField(blank=True, null=True,  verbose_name="Revenue")
    total_orders = models.IntegerField(blank=True, null=True,  verbose_name="Orders")
    total_repeat_purchase_rate = models.FloatField(blank=True, null=True,  verbose_name="Repeat Purchase Rate")
    total_conversion_rate = models.FloatField(blank=True, null=True,  verbose_name="Conversion Rate")
    total_sent = models.IntegerField(blank=True, null=True,  verbose_name="Sent")
    total_open_rate = models.FloatField(blank=True, null=True,  verbose_name="Open Rate")
    total_click_rate = models.FloatField(blank=True, null=True,  verbose_name="Click Rate")
    total_unsubscribe_rate = models.FloatField(blank=True, null=True,  verbose_name="Unsubscribe Rate")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'dashboard'


class EmailTemplate(models.Model):
    """邮件Info"""
    subject = models.TextField(verbose_name="邮件标题")
    heading_text = models.TextField(verbose_name="邮件")
    logo = models.TextField(verbose_name="邮件logo")
    banner = models.TextField(verbose_name="邮件banner")
    headline = models.TextField(verbose_name="邮件headline")
    body_text = models.TextField(verbose_name="邮件body_text")
    product_list = models.TextField(verbose_name="产品列表")
    # html = models.TextField(blank=True, null=False, verbose_name="邮件html")
    customer_group_list = models.TextField(blank=True, null=True, verbose_name="邮件对应的客户组列表")
    send_rule = models.TextField(verbose_name="发送邮件规则")
    state_choices = ((0, '待解析'), (1, '已解析'), (2, '已删除'))
    state = models.SmallIntegerField(db_index=True, choices=state_choices, default=0, verbose_name="状态")
    send_type_choices = ((0, '定时邮件'), (1, '触发邮件'))
    send_type = models.SmallIntegerField(db_index=True, choices=send_type_choices, default=0, verbose_name="邮件模板发送类型")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'email_template'


class EmailRecord(models.Model):
    uuid = models.CharField(db_index=True, max_length=255, blank=True, null=False, verbose_name="邮件ID")
    # customer_group_list = models.TextField(blank=True, null=False, verbose_name="邮件对应的客户组列表")
    # store_id = models.IntegerField(verbose_name="店铺id")
    sents = models.IntegerField(blank=True, null=True,  verbose_name="发送量")
    opens = models.IntegerField(blank=True, null=True,  verbose_name="打开量")
    clicks = models.IntegerField(blank=True, null=True,  verbose_name="点击量")
    unsubscribes = models.IntegerField(blank=True, null=True,  verbose_name="退订量")
    open_rate = models.DecimalField(blank=True, null=True,  max_digits=3, decimal_places=2, verbose_name="邮件打开率")
    click_rate = models.DecimalField(blank=True, null=True,  max_digits=3, decimal_places=2, verbose_name="邮件单击率")
    unsubscribe_rate = models.DecimalField(blank=True, null=True,  max_digits=3, decimal_places=2, verbose_name="邮件退订率")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    email_template_id = models.IntegerField(blank=True, null=True,  verbose_name="模版id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'email_record'


class EmailTrigger(models.Model):
    """邮件触发器"""
    title = models.CharField(db_index=True, max_length=255, verbose_name="标题")
    description = models.TextField(blank=True, null=False, verbose_name="描述")
    open_rate = models.DecimalField(default=0.00,  max_digits=3, decimal_places=2, verbose_name="邮件打开率")
    click_rate = models.DecimalField(default=0.00,  max_digits=3, decimal_places=2, verbose_name="邮件单击率")
    members = models.IntegerField(blank=True, null=True,  verbose_name="数量")
    trigger_info = models.TextField(blank=True, null=True,  verbose_name="trigger关系")
    email_delay = models.TextField(blank=True, null=True,  verbose_name="发送邮件顺序")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'email_trigger'


class CustomerGroup(models.Model):
    """客户组"""
    uuid = models.CharField(db_index=True, max_length=255, blank=True, null=False, verbose_name="收件人列表ID")
    title = models.CharField(db_index=True, max_length=255, verbose_name="标题")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    sents = models.IntegerField(blank=True, null=True,  verbose_name="发送量")
    opens = models.IntegerField(blank=True, null=True,  verbose_name="打开量")
    clicks = models.IntegerField(blank=True, null=True,  verbose_name="点击量")
    open_rate = models.DecimalField(default=0.00,  max_digits=3, decimal_places=2, verbose_name="邮件打开率")
    click_rate = models.DecimalField(default=0.00,  max_digits=3, decimal_places=2, verbose_name="邮件单击率")
    members = models.CharField(default=0, max_length=255, verbose_name="数量")
    relation_info = models.TextField(blank=True, null=False, verbose_name="客户关系")
    customer_list = models.TextField(blank=True, null=False, verbose_name="对应客户列表")
    state_choices = ((0, '待解析'), (1, '已解析'), (2, '已删除'))
    state = models.SmallIntegerField(db_index=True, choices=state_choices, default=0, verbose_name="状态")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        unique_together = ("store", "uuid")
        db_table = 'customer_group'


class Customer(models.Model):
    """客户表"""
    uuid = models.CharField(max_length=255, db_index=True, verbose_name="客户的唯一id")
    first_name = models.CharField(blank=True, null=True, max_length=255, verbose_name="first_name")
    last_name = models.CharField(blank=True, null=True, max_length=255, verbose_name="last_name")
    customer_email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="客户邮箱")

    subscribe_time = models.DateTimeField(blank=True, null=True, verbose_name="最近购物时间")
    sign_up_time = models.DateTimeField(blank=True, null=True, verbose_name="客户登陆时间")
    last_cart_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后一次购物时间")
    last_order_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后一次订单时间")
    last_order_status_choices = ((0, 'is paid'), (1, 'is unpaid'))
    last_order_status = models.SmallIntegerField(db_index=True, choices=last_order_status_choices, blank=True, null=True, verbose_name="客户最后一次订单状态")

    last_cart_status_choices = ((0, 'is empty'), (1, 'is not empty'))
    last_cart_status = models.SmallIntegerField(db_index=True, choices=last_cart_status_choices, blank=True,
                                                 null=True, verbose_name="客户最后一次购物车状态")

    accept_marketing_choices = ((0, 'is true'), (1, 'is false'))
    accept_marketing_status = models.SmallIntegerField(db_index=True, choices=accept_marketing_choices, blank=True,
                                                null=True, verbose_name="")

    payment_amount = models.CharField(blank=True, null=True, max_length=255, verbose_name="客户付款金额")

    # last_opened_email_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后打开邮箱时间")
    # opened_email_times = models.CharField(blank=True, null=False, max_length=255, verbose_name="客户打开邮箱次数")
    #
    # last_click_email_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后单击邮箱时间")
    # clicked_email_times = models.CharField(blank=True, null=False, max_length=255, verbose_name="客户单击邮箱次数")
    orders_count = models.IntegerField(blank=True, null=True, verbose_name="订单数量")
    last_order_id = models.CharField(blank=True, null=True, max_length=255, verbose_name="last_order_id")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'customer'


class SubscriberActivity(models.Model):
    "收件人记录表"
    opt_time = models.DateTimeField(blank=True, null=True, verbose_name="客户登陆时间")
    email = models.CharField(db_index=True, max_length=255, verbose_name="客户邮件地址")
    message_uuid = models.IntegerField(db_index=True, null=True, blank=True, verbose_name="关联的邮件ID")
    type_choices = ((0, 'Opens'), (1, 'Clicks'), (2, 'Sends'))
    type = models.SmallIntegerField(default=0, verbose_name="客户操作类型")

    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'subscriber_activity'
        unique_together = ("opt_time", "email", "type", "message_uuid")


class ProductCategory(models.Model):
    """产品类目表"""
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="产品类目标题")
    url = models.CharField(max_length=255, blank=True, null=True, verbose_name="产品类目标题url")
    category_id = models.CharField(db_index=True, max_length=255,blank=True, null=True, verbose_name="产品类目id")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING, blank=True, null=True)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        unique_together = ("category_id", "store")
        db_table = 'product_category'


class Product(models.Model):
    """产品表"""
    # sku = models.CharField(db_index=True, max_length=255, verbose_name="产品标识符")
    url = models.CharField(max_length=255, blank=True, null=True, verbose_name="产品URL")
    uuid = models.CharField(max_length=64, verbose_name="产品唯一标识")
    name = models.CharField(db_index=True, max_length=255, verbose_name="产品名称")
    image_url = models.CharField(max_length=255, verbose_name="图片URL")
    product_category = models.ForeignKey(ProductCategory, on_delete=models.DO_NOTHING,blank=True, null=True)
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        unique_together = ("product_category", "uuid")
        db_table = 'product'


class OrderEvent(models.Model):
    """
    订单事件信息
    """
    event_uuid = models.CharField(max_length=255, blank=True, null=True, verbose_name="事件的唯一标识符")
    order_uuid = models.CharField(max_length=255, verbose_name="订单的唯一标识符")
    status = models.IntegerField(db_index=True, default=0, verbose_name="订单事件类型, 0-创建(未支付)，1-支付")
    # store_url = models.CharField(db_index=True, max_length=255, verbose_name="订单对应的店铺的url")
    customer_uuid = models.CharField(db_index=True,max_length=255, verbose_name="订单对应客户id")

    # [{"product": "123456", "sales": 2, "amount": 45.22}, {"product": "123456", "sales": 1, "amount": 49.22}]
    product_info = JSONField(blank=True, null=True, verbose_name="订单所涉及到的产品及其销量信息")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="订单创建时间")

    class Meta:
        managed = False
        unique_together = ("store", "order_uuid")
        db_table = 'order_event'


class CartEvent(models.Model):
    """
    购物车事件信息
    """
    event_uuid = models.CharField(max_length=255, verbose_name="购物车事件的唯一标识符")
    # store_url = models.CharField(max_length=255, verbose_name="事件对应的店铺的url")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    customer_uuid = models.CharField(max_length=255, db_index=True, verbose_name="订单对应客户id")
    product_list = models.TextField(blank=True, null=True, verbose_name="所涉及到的产品id列表, eg:['121213']")
    create_time = models.DateTimeField(auto_now=True, db_index=True, verbose_name="创建时间")

    class Meta:
        managed = False
        db_table = 'cart_event'

# class WebhookTransaction(models.Model):
#     UNPROCESSED = 1
#     PROCESSED = 2
#     ERROR = 3
#     STATUSES = (
#         (UNPROCESSED, 'Unprocessed'),
#         (PROCESSED, 'Processed'),
#         (ERROR, 'Error'),
#     )
#     date_generated = models.DateTimeField()
#     date_received = models.DateTimeField(default=timezone.now)
#     body = hstore.SerializedDictionaryField()
#     request_meta = hstore.SerializedDictionaryField()
#     status = models.CharField(max_length=250, choices=STATUSES, default=UNPROCESSED)
#     objects = hstore.HStoreManager()
#
#     def __unicode__(self):
#         return u'{0}'.format(self.date_event_generated)

#
# class Message(models.Model):
#     date_processed = models.DateTimeField(default=timezone.now)
#     webhook_transaction = models.OneToOneField(WebhookTransaction)
#
#     team_id = models.CharField(max_length=250)
#     team_domain = models.CharField(max_length=250)
#     channel_id = models.CharField(max_length=250)
#     channel_name = models.CharField(max_length=250)
#     user_id = models.CharField(max_length=250)
#     user_name = models.CharField(max_length=250)
#     text = models.TextField()
#     trigger_word = models.CharField(max_length=250)
#
#     def __unicode__(self):
#         return u'{}'.format(self.user_name)
#
#     """
#     pass

#

# class WebhookTransaction(models.Model):
#     UNPROCESSED = 1
#     PROCESSED = 2
#     ERROR = 3
#     STATUSES = (
#         (UNPROCESSED, 'Unprocessed'),
#         (PROCESSED, 'Processed'),
#         (ERROR, 'Error'),
#     )
#     date_generated = models.DateTimeField()
#     date_received = models.DateTimeField(default=timezone.now)
#     body = hstore.SerializedDictionaryField()
#     request_meta = hstore.SerializedDictionaryField()
#     status = models.CharField(max_length=250, choices=STATUSES, default=UNPROCESSED)
#     objects = hstore.HStoreManager()
#
#     def __unicode__(self):
#         return u'{0}'.format(self.date_event_generated)
#
#
# class Message(models.Model):
#     date_processed = models.DateTimeField(default=timezone.now)
#     webhook_transaction = models.OneToOneField(WebhookTransaction)
#
#     team_id = models.CharField(max_length=250)
#     team_domain = models.CharField(max_length=250)
#     channel_id = models.CharField(max_length=250)
#     channel_name = models.CharField(max_length=250)
#     user_id = models.CharField(max_length=250)
#     user_name = models.CharField(max_length=250)
#     text = models.TextField()
#     trigger_word = models.CharField(max_length=250)
#
#     def __unicode__(self):
#         return u'{}'.format(self.user_name)


# class SalesVolume(models.Model):
#     """销售量"""
#     three_val = models.TextField(blank=True, null=True, verbose_name="前三天的销售量")
#     seven_val = models.TextField(blank=True, null=True, verbose_name="前七天的销售量")
#     fifteen_val = models.TextField(blank=True, null=True, verbose_name="前十五天的销售量")
#     thirty_val = models.TextField(blank=True, null=True, verbose_name="前三十天的销售量")
#     create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
#     update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
#
#     class Meta:
#         managed = False
#         db_table = 'sales_volume'
