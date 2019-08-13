from django.conf.urls import url, include
from app.views import shopify_auth, personal_center, service, webhook, opstores_service


auth_urlpatterns = [

    url(r'shopify/callback/$', shopify_auth.ShopifyCallback.as_view()),
    url(r'shopify/ask_permission/$', shopify_auth.ShopifyAuthView.as_view()),

]


v1_urlpatterns = [

    # 注册 登陆
    url(r'^account/login/$', personal_center.LoginView.as_view()),
    # shopfy注册设置密码-->注册
    url(r'^account/set_password/(?P<pk>[0-9]+)/$', personal_center.SetPasswordView.as_view()),
    # 登陆状态下设置密码
    url(r'^account/set_passwords/(?P<pk>[0-9]+)/$', personal_center.SetPasswordsView.as_view()),


    # 客户组
    url(r'^customer_group/$', service.CustomerGroupView.as_view()),
    url(r'^customer_group/(?P<pk>[0-9]+)/$', service.CustomerGroupOptView.as_view()),

    # 邮件管理
    url(r'^email_template/$', service.EmailTemplateView.as_view()),                         # 模板列表，创建模板
    url(r'^email_template/trigger/$', service.TriggerEmailTemplateView.as_view()),          # 通过flow创建邮件模板
    url(r'^email_template/detail/(?P<pk>[0-9]+)/$', service.EmailTemplateRetrieveView.as_view()),  # 模板详情
    url(r'^email_template/(?P<pk>[0-9]+)/$', service.EmailTemplateUpdateView.as_view()),    # 更改状态

    url(r'^top_product/$', service.TopProductView.as_view()),
    url(r'^upload_picture/$', service.UploadPicture.as_view()),

    # 邮件触发器
    url(r'^email_trigger/$', service.EmailTriggerView.as_view()),
    url(r'^email_trigger/(?P<pk>[0-9]+)/$', service.EmailTriggerOptView.as_view()),
    url(r'^email_trigger/(?P<pk>[0-9]+)/$', service.EmailTriggerOptView.as_view()),         # 模板克隆

    # 测试发送邮件
    url(r'^send_mail/$', service.SendMailView.as_view()),


    # dashboard
    url(r'^top_dashboard/$', service.TopDashboardView.as_view()),
    url(r'^bottom_dashboard/$', service.BottomDashboardView.as_view()),


    # 店铺管理
    url(r'store/$', service.StoreView.as_view()),
    url(r'store/(?P<pk>[0-9]+)/$', service.StoreOperView.as_view()),


]


webhook_urlpatterns = [

    # url(r'order/update/$', webhook.EventOrderUpdate.as_view()),
    # url(r'order/create/$', webhook.EventOrderCreate.as_view()),
    url(r'order/paid/$', webhook.EventOrderPaid.as_view()),

    url(r'customers/create/$', webhook.EventDraftCustomersCreate.as_view()),
    url(r'customers/update/$', webhook.EventDraftCustomersUpdate.as_view()),

    url(r'checkouts/create/$', webhook.CheckoutsCreate.as_view()),
    url(r'checkouts/update/$', webhook.CheckoutsUpdate.as_view()),
    url(r'checkouts/delete/$', webhook.CheckoutsDelete.as_view()),

    url(r'cart/update/$', webhook.CartsUpdate.as_view()),

]


v2_urlpatterns = [
    url(r'opstores/store/$', opstores_service.StoreInitViews.as_view()),                # 店铺授权
    url(r'email_trigger/$', opstores_service.EmailTriggerView.as_view()),              # flow列表
    url(r'email_trigger/(?P<pk>[0-9]+)/$', opstores_service.EmailTriggerOptView.as_view()),     # flow状态修改

    url(r'email_template/$', opstores_service.EmailTemplateView.as_view()),                     # 模板列表
    url(r'email_template/(?P<pk>[0-9]+)/$', opstores_service.EmailTemplateUpdateView.as_view()),         # 模板更改状态
    url(r'email_template/detail/(?P<pk>[0-9]+)/$', opstores_service.EmailTemplateRetrieveView.as_view()),     # 模板详情
]



urlpatterns = [
    url(r'^v1/auth/', include(auth_urlpatterns)),
    url(r'^v1/webhook/', include(webhook_urlpatterns)),
    url(r'^v1/', include(v1_urlpatterns)),
    url(r'^v2/', include(v2_urlpatterns)),
]
