from django.conf.urls import url, include
from app.views import shopify_auth, personal_center, service


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

]

urlpatterns = [
    url(r'^v1/auth/', include(auth_urlpatterns)),
    url(r'^v1/', include(v1_urlpatterns)),
]
