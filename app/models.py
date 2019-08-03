from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
# from django_hstore import hstore
from django_mysql.models import JSONField

# 迁移之前将期改为True
ENABLE_MIGRATE = False


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
    init_choices = ((0, '新店铺'), (1, '旧店铺'))
    init = models.SmallIntegerField(db_index=True, choices=init_choices, default=0, verbose_name="店铺初始化")
    # order_init_choices = ((0, '新店铺没有拉过order'), (1, '拉过一次数据'))
    # order_init = models.SmallIntegerField(db_index=True, choices=order_init_choices, default=0, verbose_name="店铺是否拉过order")
    # customer_init_choices = ((0, '新店铺没有拉过customer'), (1, '拉过一次数据'))
    # customer_init = models.SmallIntegerField(db_index=True, choices=customer_init_choices, default=0, verbose_name="店铺是否拉过customer")
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING, blank=True, null=True, unique=True)
    store_create_time = models.DateTimeField(blank=True, null=True, verbose_name="店铺创建时间")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        db_table = 'store'


class Dashboard(models.Model):
    """Dashboard"""
    revenue = models.FloatField(default=0, blank=True, null=True, verbose_name="Revenue")
    orders = models.IntegerField(default=0, blank=True, null=True, verbose_name="Orders")
    # repeat_purchase_rate = models.FloatField(blank=True, null=True,  verbose_name="Repeat Purchase Rate")
    # conversion_rate = models.FloatField(blank=True, null=True,   verbose_name="Conversion Rate")
    # delta_sent = models.IntegerField(blank=True, null=True,  verbose_name="Sent 增量")
    # delta_open = models.IntegerField(blank=True, null=True,  verbose_name="Open 增量")
    # delta_click = models.IntegerField(blank=True, null=True,  verbose_name="Click 增量")
    # open_rate = models.FloatField(blank=True, null=True,  verbose_name="Open Rate")
    # click_rate = models.FloatField(blank=True, null=True,  verbose_name="Click Rate")
    # unsubscribe_rate = models.FloatField(blank=True, null=True,  verbose_name="Unsubscribe Rate")
    total_revenue = models.FloatField(default=0, blank=True, null=True,  verbose_name="Revenue")
    total_orders = models.IntegerField(default=0, blank=True, null=True,   verbose_name="Orders")
    total_sessions = models.IntegerField(default=0, blank=True, null=True, verbose_name="sessions总量")
    session = models.IntegerField(default=0, blank=True, null=True, verbose_name="session")
    avg_repeat_purchase_rate = models.FloatField(default=0, blank=True, null=True,  verbose_name="Repeat Purchase Rate")
    avg_conversion_rate = models.FloatField(default=0, blank=True, null=True,  verbose_name="Conversion Rate")
    total_sent = models.IntegerField(default=0, blank=True, null=True, verbose_name="Sent总量")
    total_open = models.IntegerField(default=0, blank=True, null=True, verbose_name="Open总量")
    total_click = models.IntegerField(default=0, blank=True, null=True,  verbose_name="Click总量")
    total_unsubscribe = models.IntegerField(default=0, blank=True, null=True,  verbose_name="Unsubscribe总量")
    avg_open_rate = models.FloatField(default=0, blank=True, null=True,  verbose_name="Open Rate")
    avg_click_rate = models.FloatField(default=0, blank=True, null=True,  verbose_name="Click Rate")
    avg_unsubscribe_rate = models.FloatField(default=0, blank=True, null=True,  verbose_name="Unsubscribe Rate")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        db_table = 'dashboard'


class EmailTemplate(models.Model):
    """邮件模版"""
    title = models.CharField(db_index=True, blank=True, null=True, max_length=255, verbose_name="标题")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    subject = models.TextField(verbose_name="邮件标题")
    heading_text = models.TextField(verbose_name="邮件")
    revenue = models.DecimalField(default=0, max_digits=10, decimal_places=4, verbose_name="对应的销售额")
    sessions = models.IntegerField(default=0, verbose_name="流量数")
    transcations = models.IntegerField(default=0, verbose_name="交易次数")
    logo = models.TextField(verbose_name="邮件logo")
    banner = models.TextField(verbose_name="邮件banner")
    headline = models.TextField(verbose_name="邮件headline")
    body_text = models.TextField(verbose_name="邮件body_text")
    # top_type = models.TextField(verbose_name="选择的哪类top product")
    product_list = models.TextField(verbose_name="产品列表", blank=True, null=True)
    # html = models.TextField(blank=True, null=False, verbose_name="邮件html")
    customer_group_list = models.TextField(verbose_name="邮件对应的客户组列表")
    send_rule = models.TextField(verbose_name="发送邮件规则")
    status_choices = ((0, '待解析'), (1, '已解析'), (2, '已删除'))
    status = models.SmallIntegerField(db_index=True, choices=status_choices, default=0, verbose_name="状态")
    enable_choice = ((0, '禁用'), (1, '启用'))
    enable = models.SmallIntegerField(default=0,choices=enable_choice, verbose_name="是否启用")
    send_type_choices = ((0, '定时邮件'), (1, '触发邮件'), (3, '测试邮件'))
    send_type = models.SmallIntegerField(db_index=True, choices=send_type_choices, default=0, verbose_name="邮件模板发送类型")
    html = models.TextField(blank=True, null=True, verbose_name="描述")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        db_table = 'email_template'
        ordering = ["-id"]


class EmailRecord(models.Model):
    uuid = models.CharField(db_index=True, max_length=255, blank=True, null=False, verbose_name="邮件ID")
    # customer_group_list = models.TextField(blank=True, null=False, verbose_name="邮件对应的客户组列表")
    sents = models.IntegerField(blank=True, null=True,  verbose_name="发送量")
    opens = models.IntegerField(blank=True, null=True,  verbose_name="打开量")
    clicks = models.IntegerField(blank=True, null=True,  verbose_name="点击量")
    unsubscribes = models.IntegerField(blank=True, null=True,  verbose_name="退订量")
    open_rate = models.DecimalField(blank=True, null=True,  max_digits=10, decimal_places=4, verbose_name="邮件打开率")
    click_rate = models.DecimalField(blank=True, null=True,  max_digits=10, decimal_places=4, verbose_name="邮件单击率")
    unsubscribe_rate = models.DecimalField(blank=True, null=True,  max_digits=10, decimal_places=4, verbose_name="邮件退订率")
    type_choice = ((0, 'Newsletter'), (1, 'Transactional'), (2, 'Test'))
    type = models.SmallIntegerField(blank=True, null=True, verbose_name="邮件类型")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    email_template_id = models.IntegerField(blank=True, null=True,  verbose_name="模版id")  # type=0时使用的参数
    email_trigger_id = models.IntegerField(blank=True, null=True,  verbose_name="邮件触发器id")  # type=1时使用的参数
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        db_table = 'email_record'


class EmailTrigger(models.Model):
    """邮件触发器"""
    customer_list_id = models.CharField(db_index=True, max_length=255, blank=True, null=True, verbose_name="flows筛选出来的ListId")
    title = models.CharField(db_index=True, max_length=255, verbose_name="标题")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    open_rate = models.DecimalField(default=0,  max_digits=10, decimal_places=4, verbose_name="邮件打开率")
    click_rate = models.DecimalField(default=0,  max_digits=10, decimal_places=4, verbose_name="邮件单击率")
    revenue = models.DecimalField(default=0,  max_digits=10, decimal_places=4, verbose_name="对应的销售额")
    # members = models.IntegerField(blank=True, null=True,  verbose_name="数量")
    relation_info = models.TextField(blank=True, null=True, verbose_name="筛选条件")
    email_delay = models.TextField(blank=True, null=True, verbose_name="发送邮件顺序")
    customer_list = models.TextField(blank=True, null=True, verbose_name="对应客户列表")
    # note_choice = ((0, 'Do not send if the customer if your customer makes a purchase. && Do not send if the customer received an email from this campaign in the last 7 days.'),
    #                (1, 'Do not send if the customer if your customer makes a purchase.'),
    #                (2, 'Do not send if the customer received an email from this campaign in the last 7 days.'))
    note = models.TextField(default="[]", verbose_name="对应Note列表")
    status_choice = ((0, 'disable'), (1, 'enable'), (2, 'delete'))
    status = models.SmallIntegerField(default=0, verbose_name="邮件类型")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    create_time = models.DateTimeField(db_index=True,auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True,auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        db_table = 'email_trigger'
        ordering = ["-id"]


class EmailTask(models.Model):
    template = models.ForeignKey(EmailTemplate, blank=True, null=True, on_delete=models.DO_NOTHING)
    uuid = models.CharField(db_index=True, max_length=255, blank=True, null=True, verbose_name="事务邮件ID")
    status_choices = ((0, '待发送'), (1, '已发送(成功)'),(2, '已发送但发送失败'), (3, '模版禁用'), (4, "模板已删除"))
    status = models.SmallIntegerField(db_index=True, choices=status_choices, default=0, verbose_name="邮件发送状态")
    remark = models.TextField(blank=True, null=True, verbose_name="备注")
    execute_time = models.DateTimeField(db_index=True, verbose_name="执行时间")
    finished_time = models.DateTimeField(blank=True, null=True, verbose_name="完成时间")
    customer_list = models.TextField(blank=True, null=True, verbose_name="符合触发条件的用户列表")
    if ENABLE_MIGRATE:
        email_trigger_id = models.IntegerField(db_index=True, default=None, verbose_name="email_trigger_id")
    else:
        email_trigger = models.ForeignKey(EmailTrigger, blank=True, null=True, on_delete=models.DO_NOTHING)

    type_choices = ((0, 'Timed mail'), (1, 'Trigger mail'))
    type = models.SmallIntegerField(db_index=True, choices=type_choices, default=0, verbose_name="邮件类型")
    create_time = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        db_table = 'email_task'


class CustomerGroup(models.Model):
    """客户组"""
    uuid = models.CharField(db_index=True, max_length=255, blank=True, null=True, verbose_name="收件人列表ID")
    title = models.CharField(db_index=True, max_length=255, verbose_name="标题")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    sents = models.IntegerField(blank=True, null=True,  verbose_name="发送量")
    opens = models.IntegerField(blank=True, null=True,  verbose_name="打开量")
    clicks = models.IntegerField(blank=True, null=True,  verbose_name="点击量")
    open_rate = models.DecimalField(default=0.00,  max_digits=10, decimal_places=4, verbose_name="邮件打开率")
    click_rate = models.DecimalField(default=0.00,  max_digits=10, decimal_places=4, verbose_name="邮件单击率")
    members = models.CharField(default=0, max_length=255, verbose_name="数量")
    relation_info = models.TextField(blank=True, null=True, verbose_name="客户关系")
    customer_list = models.TextField(blank=True, null=True, verbose_name="对应客户列表")
    state_choices = ((0, '待解析'), (1, '已解析'), (2, '已删除'))
    state = models.SmallIntegerField(db_index=True, choices=state_choices, default=0, verbose_name="状态")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        db_table = 'customer_group'


class Customer(models.Model):
    """客户表"""
    uuid = models.CharField(max_length=255, db_index=True, verbose_name="客户的唯一id")
    first_name = models.CharField(blank=True, null=True, max_length=255, verbose_name="first_name")
    last_name = models.CharField(blank=True, null=True, max_length=255, verbose_name="last_name")
    customer_email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="客户邮箱")
    subscribe_time = models.DateTimeField(blank=True, null=True, verbose_name="最近购物时间")
    sign_up_time = models.DateTimeField(blank=True, null=True, db_index=True, verbose_name="客户登陆时间")
    last_cart_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后一次购物时间")
    last_order_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后一次订单时间")
    last_order_status_choices = ((0, 'is paid'), (1, 'is unpaid'))
    last_order_status = models.SmallIntegerField(db_index=True, choices=last_order_status_choices, blank=True, null=True, verbose_name="客户最后一次订单状态")
    last_cart_status_choices = ((0, 'is empty'), (1, 'is not empty'))
    last_cart_status = models.SmallIntegerField(db_index=True, choices=last_cart_status_choices, blank=True,
                                                 null=True, verbose_name="客户最后一次购物车状态")

    accept_marketing_choices = ((0, 'is true'), (1, 'is false'))
    accept_marketing_status = models.SmallIntegerField(db_index=True, choices=accept_marketing_choices, blank=True,null=True, verbose_name="")

    unsubscribe_choices = ((0, 'is false'), (1, 'is true'), (2, 'is sleep'))
    unsubscribe_status = models.SmallIntegerField(db_index=True, choices=unsubscribe_choices, default=0, verbose_name="取消订阅或者休眠")
    unsubscribe_date = models.DateTimeField(blank=True, null=True, verbose_name="取消订阅时间/休眠的截止时间")  # unsubscribe_status=1时为取消订阅时间，unsubscribe_status=2时为休眠的截止时间

    payment_amount = models.CharField(blank=True, null=True, max_length=255, verbose_name="客户付款金额")

    # last_opened_email_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后打开邮箱时间")
    # opened_email_times = models.CharField(blank=True, null=False, max_length=255, verbose_name="客户打开邮箱次数")
    #
    # last_click_email_time = models.DateTimeField(blank=True, null=True, verbose_name="客户最后单击邮箱时间")
    # clicked_email_times = models.CharField(blank=True, null=False, max_length=255, verbose_name="客户单击邮箱次数")
    orders_count = models.IntegerField(blank=True, null=True, verbose_name="订单数量")
    last_order_id = models.CharField(blank=True, null=True, max_length=255, verbose_name="last_order_id")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    create_time = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        if ENABLE_MIGRATE:
            unique_together = ("store_id", "uuid")
        else:
            unique_together = ("store", "uuid")
        db_table = 'customer'


class SubscriberActivity(models.Model):
    "收件人记录表"
    opt_time = models.DateTimeField(blank=True, null=True, verbose_name="客户登陆时间")
    email = models.CharField(db_index=True, max_length=255, verbose_name="客户邮件地址")
    message_uuid = models.IntegerField(db_index=True, null=True, blank=True, verbose_name="关联的邮件ID")
    type_choices = ((0, 'Opens'), (1, 'Clicks'), (2, 'Sends'))
    type = models.SmallIntegerField(default=0, verbose_name="客户操作类型")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = False
        db_table = 'subscriber_activity'


class ProductCategory(models.Model):
    """产品类目表"""
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="产品类目标题")
    url = models.CharField(max_length=255, blank=True, null=True, verbose_name="产品类目标题url")
    category_id = models.CharField(db_index=True, max_length=255,blank=True, null=True, verbose_name="产品类目id")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING, blank=True)
    create_time = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        if ENABLE_MIGRATE:
            unique_together = ("category_id", "store_id")
        else:
            unique_together = ("category_id", "store")
        db_table = 'product_category'


class Product(models.Model):
    """产品表"""
    # sku = models.CharField(db_index=True, max_length=255, verbose_name="产品标识符")
    url = models.CharField(max_length=255, blank=True, null=True, verbose_name="产品URL")
    uuid = models.CharField(max_length=64, verbose_name="产品唯一标识")
    name = models.CharField(db_index=True, max_length=255, verbose_name="产品名称")
    image_url = models.CharField(max_length=255, verbose_name="图片URL")
    price = models.CharField(blank=True, null=True, max_length=255, verbose_name="产品价格")
    product_category = models.ForeignKey(ProductCategory, on_delete=models.DO_NOTHING,blank=True, null=True)
    state = models.SmallIntegerField(default=0, verbose_name="前端判断是否勾选状态")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        unique_together = ("product_category", "uuid")
        db_table = 'product'


class OrderEvent(models.Model):
    """
    订单事件信息
    """
    event_uuid = models.CharField(max_length=255, blank=True, null=True, verbose_name="事件的唯一标识符")
    order_uuid = models.CharField(max_length=255, verbose_name="订单的唯一标识符")
    checkout_id = models.CharField(db_index=True, max_length=255, verbose_name="checkout的唯一标识符")
    status = models.IntegerField(db_index=True, default=0, verbose_name="订单事件类型, 0-创建(未支付)，1-支付")
    status_tag = models.CharField(max_length=255, blank=True, null=True, verbose_name="订单类型tag")
    status_url = models.CharField(max_length=255, blank=True, null=True, verbose_name="订单类型url")
    # store_url = models.CharField(db_index=True, max_length=255, verbose_name="订单对应的店铺的url")
    customer_uuid = models.CharField(db_index=True,max_length=255, verbose_name="订单对应客户id")
    # [{"product": "123456", "sales": 2, "amount": 45.22}, {"product": "123456", "sales": 1, "amount": 49.22}]
    product_info = JSONField(blank=True, null=True, verbose_name="订单所涉及到的产品及其销量信息")
    total_price = models.CharField(blank=True, null=True, max_length=255, verbose_name="订单总金额")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    order_create_time = models.DateTimeField(db_index=True, blank=True, null=True, verbose_name="订单创建时间")
    order_update_time = models.DateTimeField(db_index=True, blank=True, null=True, verbose_name="订单更新时间")
    create_time = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        if ENABLE_MIGRATE:
            unique_together = ("store_id", "order_uuid")
        else:
            unique_together = ("store", "order_uuid")

        db_table = 'order_event'


class CheckoutEvent(models.Model):
    """
    checkout事件信息
    """
    checkout_id = models.CharField(db_index=True, max_length=255, verbose_name="checkout的唯一标识符")
    customer_uuid = models.CharField(max_length=255, db_index=True, verbose_name="订单对应客户id")
    #product_list = models.TextField(blank=True, null=True, verbose_name="所涉及到的产品id列表, eg:['121213']")
    abandoned_checkout_url = models.TextField(blank=True, null=True, verbose_name="checkout_url")
    status = models.IntegerField(db_index=True, default=0, verbose_name="checkouts事件类型, 0-创建(未支付)，1-支付, 2-删除")
    product_info = JSONField(blank=True, null=True, verbose_name="订单所涉及到的产品及其销量信息")
    total_price = models.CharField(blank=True, null=True, max_length=255, verbose_name="订单总金额")
    checkout_create_time = models.DateTimeField(db_index=True, blank=True, null=True, verbose_name="订单创建时间")
    checkout_update_time = models.DateTimeField(db_index=True, blank=True, null=True, verbose_name="订单更新时间")
    cart_token = models.CharField(db_index=True,blank=True, null=True, max_length=255, verbose_name="cart_token")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    create_time = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")
    update_time = models.DateTimeField(db_index=True, auto_now=True, verbose_name="更新时间")
    email_date = models.DateTimeField(db_index=True, blank=True, null=True, verbose_name="最后一次邮件通知时间，为空代表还没有发送过促销邮件")

    class Meta:
        managed = ENABLE_MIGRATE
        db_table = 'checkout_event'


class TopProduct(models.Model):
    """TopProduct"""
    top_three = models.TextField(blank=True, null=True, verbose_name="前三天的销售量")
    top_seven = models.TextField(blank=True, null=True, verbose_name="前七天的销售量")
    top_fifteen = models.TextField(blank=True, null=True, verbose_name="前十五天的销售量")
    top_thirty = models.TextField(blank=True, null=True, verbose_name="前三十天的销售量")
    if ENABLE_MIGRATE:
        store_id = models.IntegerField(db_index=True, verbose_name="店铺id")
    else:
        store = models.ForeignKey(Store, on_delete=models.DO_NOTHING)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        managed = ENABLE_MIGRATE
        db_table = 'top_product'
