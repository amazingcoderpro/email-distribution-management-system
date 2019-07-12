from django.contrib.auth.models import AbstractUser
from django.db import models


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
    url = models.CharField(blank=True, null=False, max_length=255, unique=True, verbose_name="店铺URL")
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
    subject = models.TextField(blank=True, null=False, verbose_name="邮件标题")
    heading_text = models.TextField(blank=True, null=False, verbose_name="邮件")
    logo = models.TextField(blank=True, null=False, verbose_name="邮件logo")
    banner = models.TextField(blank=True, null=False, verbose_name="邮件banner")
    headline = models.TextField(blank=True, null=False, verbose_name="邮件headline")
    body_text = models.TextField(blank=True, null=False, verbose_name="邮件body_text")
    product_list = models.TextField(blank=True, null=False, verbose_name="产品列表")
    # html = models.TextField(blank=True, null=False, verbose_name="邮件html")
    customer_group_list = models.TextField(blank=True, null=False, verbose_name="邮件对应的客户组列表")
    send_rule = models.TextField(blank=True, null=False, verbose_name="发送邮件规则")
    state_choices = ((0, '定时邮件'), (1, '触发邮件'))
    state = models.SmallIntegerField(db_index=True, choices=state_choices, default=0, verbose_name="邮件模板类型")
    #store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        #managed = False
        db_table = 'email_template'


class EmailRecord(models.Model):
    uuid = models.CharField(db_index=True, max_length=255, blank=True, null=False, verbose_name="邮件ID")
    customer_group_list = models.TextField(blank=True, null=False, verbose_name="邮件对应的客户组列表")
    store_id = models.IntegerField(verbose_name="店铺id")
    sents = models.IntegerField(blank=True, null=True,  verbose_name="发送量")
    opens = models.IntegerField(blank=True, null=True,  verbose_name="打开量")
    clicks = models.IntegerField(blank=True, null=True,  verbose_name="点击量")
    unsubscribes = models.IntegerField(blank=True, null=True,  verbose_name="退订量")
    open_rate = models.DecimalField(blank=True, null=True,  max_digits=3, decimal_places=2, verbose_name="邮件打开率")
    click_rate = models.DecimalField(blank=True, null=True,  max_digits=3, decimal_places=2, verbose_name="邮件单击率")
    unsubscribe_rate = models.DecimalField(blank=True, null=True,  max_digits=3, decimal_places=2, verbose_name="邮件退订率")
    #store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        #managed = False
        db_table = 'email_record'


class EmailTrigger(models.Model):
    """邮件触发器"""
    title = models.CharField(db_index=True, max_length=255, verbose_name="标题")
    description = models.TextField(blank=True, null=False, verbose_name="描述")
    open_rate = models.FloatField(blank=True, null=True,  verbose_name="打开邮件比例")
    click_rate = models.FloatField(blank=True, null=True,  verbose_name="单击比例")
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
    open_rate = models.DecimalField(blank=True, null=True,  max_digits=3, decimal_places=2, verbose_name="邮件打开率")
    click_rate = models.DecimalField(blank=True, null=True,  max_digits=3, decimal_places=2, verbose_name="邮件单击率")
    members = models.CharField(blank=True, null=True, max_length=255, verbose_name="数量")
    relation_info = models.TextField(blank=True, null=False, verbose_name="客户关系")
    customer_list = models.TextField(blank=True, null=False, verbose_name="对应客户列表")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'customer_group'


class Customer(models.Model):
    """客户表"""
    name = models.CharField(max_length=255, verbose_name="客户名称")
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

    payment_amount = models.CharField(blank=True, null=False, max_length=255, verbose_name="客户付款金额")

    # last_opened_email_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后打开邮箱时间")
    # opened_email_times = models.CharField(blank=True, null=False, max_length=255, verbose_name="客户打开邮箱次数")
    #
    # last_click_email_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后单击邮箱时间")
    # clicked_email_times = models.CharField(blank=True, null=False, max_length=255, verbose_name="客户单击邮箱次数")

    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'customer'


class SubscriberActivity(models.Model):
    opt_time = models.DateTimeField(blank=True, null=True, verbose_name="客户登陆时间")
    email = models.CharField(db_index=True, max_length=255, verbose_name="客户邮件地址")
    message_uuid = models.IntegerField(db_index=True, null=True, blank=True, verbose_name="关联的邮件ID")
    type_choices = ((0, 'Opens'), (1, 'Clicks'))
    type = models.SmallIntegerField(default=0, verbose_name="客户操作类型")

    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'subscriber_activity'
        unique_together = ("opt_time", "email", "type")


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
    sku = models.CharField(db_index=True, max_length=255, verbose_name="产品标识符")
    url = models.CharField(max_length=255, blank=True, null=True, verbose_name="产品URL")
    uuid = models.CharField(max_length=64, verbose_name="产品唯一标识")
    name = models.CharField(db_index=True, max_length=255, verbose_name="产品名称")
    image_url = models.CharField(max_length=255, verbose_name="图片URL")
    thumbnail = models.TextField(verbose_name="缩略图", blank=True, null=True, default=None)
    price = models.CharField(max_length=255, verbose_name="产品价格")
    product_category = models.ForeignKey(ProductCategory, on_delete=models.DO_NOTHING,blank=True, null=True)
    tag = models.CharField(max_length=255, verbose_name="所属标签")
    store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    #store_id = models.IntegerField(verbose_name="店铺id")
    publish_time = models.DateTimeField(blank=True, null=True, verbose_name="发布时间")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    url_with_utm = models.CharField(db_index=True, blank=True, null=True, max_length=255, verbose_name=u"产品的带utm构建的url")

    class Meta:
        managed = False
        unique_together = ("product_category", "uuid")
        db_table = 'product'