## edm项目

### 1. 数据库初始化

```

INSERT INTO `store` (`id`, `name`, `url`, `domain`, `email`, `token`, `hmac`, `timezone`, `sender`, `customer_shop`, `sender_address`, `logo`, `service_email`, `currency`, `site_name`, `store_view_id`, `init`, `source`, `user_id`, `store_create_time`, `create_time`, `update_time`)
VALUES
	(1, 'admin', 'admin.myshopify.com', 'www.admin.com', '', '', '', '(GMT+08:00) Asia/Shanghai', 'admin', '', '', NULL, NULL, NULL, NULL, '111111', 1, 1, 1, '2018-08-15 10:39:16.000000', '2019-07-12 09:53:09.077657', '2019-08-07 17:51:30.943595');



INSERT INTO `user` (`id`, `last_login`, `is_superuser`, `first_name`, `last_name`, `is_staff`, `is_active`, `date_joined`, `username`, `email`, `password`, `code`, `create_time`, `update_time`)
VALUES
	(1, NULL, 0, '', '', 0, 1, '2019-07-12 09:53:09.453778', 'admin', '', 'pbkdf2_sha256$120000$6YoSxUhSYlrw$6bJxEh1+uJVQ8cwm47KIzbwXPpmm3lz0qgQmbMr3yKE=', '111111', '2019-07-12 09:53:09.454534', '2019-08-01 14:42:03.904975');


INSERT INTO `customer_group` (`id`, `title`, `description`, `sents`, `opens`, `clicks`, `open_rate`, `click_rate`, `members`, `relation_info`, `customer_list`, `state`, `store_id`, `create_time`, `update_time`)
VALUES
	(1, 'VIP Customers', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"VIP Customers\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer placed order\",\"relations\":[{\"relation\":\"more than\",\"values\":[\"3\",1],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer total order payment amount\",\"relations\":[{\"relation\":\"is more than\",\"values\":[500],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"Accept Marketings\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:04:30.152421', '2019-08-16 13:38:27.824821'),
	(2, 'New ArrivalsNew Customers', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"New ArrivalsNew Customers\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer sign up time\",\"relations\":[{\"relation\":\"is in the past\",\"values\":[15,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer subscribe time\",\"relations\":[{\"relation\":\"is in the past\",\"values\":[15,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer placed order\",\"relations\":[{\"relation\":\"equals\",\"values\":[\"0\"],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"New ArrivalsNew Customers\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:08:56.527726', '2019-08-16 13:38:27.832379'),
	(3, 'Potential Customers', 'Potential Customers', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"Potential Customers\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer paid order\",\"relations\":[{\"relation\":\"equals\",\"values\":[\"0\"],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer placed order\",\"relations\":[{\"relation\":\"more than\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is in the past\",\"values\":[60,1],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"Accept Marketings\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:09:31.025966', '2019-08-16 13:38:27.839564'),
	(4, 'At Churn-Risk Custome', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"At Churn-Risk Custome\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer placed order\",\"relations\":[{\"relation\":\"more than\",\"values\":[\"1\",1],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer last order created time\",\"relations\":[{\"relation\":\"is between\",\"values\":[30,90],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"At Churn-Risk Custome\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:15:13.429793', '2019-08-16 13:38:27.847500'),
	(5, 'Lapsed Customers', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"Lapsed Customers\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer last order created time\",\"relations\":[{\"relation\":\"is between\",\"values\":[90,100000],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer clicked email\",\"relations\":[{\"relation\":\"equals\",\"values\":[\"0\"],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"Lapsed Customers\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:21:33.202815', '2019-08-16 13:38:27.855510'),
	(6, 'Active Customers', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"Active Customers\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer last order created time\",\"relations\":[{\"relation\":\"is in the past\",\"values\":[30,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer last opened email time\",\"relations\":[{\"relation\":\"is in the past\",\"values\":[30,1],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"Active Customers\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:25:27.987085', '2019-08-16 13:38:27.861897');

```

### 2. 部署

```
## 安装python3
https://www.cnblogs.com/golangav/p/7341870.html#_label0



## 1.拉取后端项目

mkdir -p /data/django/ && mkdir /data/nginx/ && cd /data/django/
git clone https://github.com/wcadaydayup/edm.git
cd /data/django/edm/ && pipenv install


## 2.拉取前端项目

mkdir -p /data/nginx/edm/
将前端dist目录传到/data/nginx/edm/下
mkdir /data/nginx/edm/dist/media/


## 3.安装supervisor

yum install epel-release
yum install -y supervisor
systemctl enable supervisord
mv /data/django/edm/bin/supervisord/supervisord.conf /etc/supervisord.conf
vim /etc/supervisord.conf         # 将mysql环境变量写到配置文件中
    environment=

systemctl start supervisord
systemctl status supervisord


## 4.安装nginx

rpm -Uvh http://nginx.org/packages/centos/7/noarch/RPMS/nginx-release-centos-7-0.el7.ngx.noarch.rpm
yum install -y nginx
systemctl enable nginx.service
vim /etc/nginx/conf.d/edm.conf

    upstream server_pools {
        server 127.0.0.1:8000; # for a web port socket (we'll use this first)
    }

    server {
        listen       80;
        server_name  smartsend.seamarketings.com;
        location /api {
             proxy_pass http://server_pools;
             proxy_set_header   Host             $host;
             proxy_set_header   X-Forwarded-For        $remote_addr;
        }
        location / {
            root   /data/nginx/edm/dist;
            index  index.html index.htm;
            error_page 404 /index.html;
        }
    }
systemctl start nginx.service


```
















