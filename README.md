# edm

## user store 初始化

```

INSERT INTO `user` (`id`, `last_login`, `is_superuser`, `first_name`, `last_name`, `is_staff`, `is_active`, `date_joined`, `username`, `email`, `password`, `code`, `create_time`, `update_time`)
VALUES
	(1, NULL, 0, '', '', 0, 1, '2019-07-12 09:53:09.453778', 'admin', '', 'pbkdf2_sha256$120000$6YoSxUhSYlrw$6bJxEh1+uJVQ8cwm47KIzbwXPpmm3lz0qgQmbMr3yKE=', '111111', '2019-07-12 09:53:09.454534', '2019-08-01 14:42:03.904975');


INSERT INTO `store` (`id`, `name`, `url`, `domain`, `email`, `token`, `hmac`, `timezone`, `sender`, `customer_shop`, `sender_address`, `store_view_id`, `init`, `source`, `store_create_time`, `create_time`, `update_time`, `user_id`)
VALUES
	(1, 'admin', '', '', '', '', '', '(GMT+08:00) Asia/Shanghai', 'admin', '', '', '195406097', 1, 1, '2018-08-15 10:39:16.000000', '2019-07-12 09:53:09.077657', '2019-08-07 17:51:30.943595', 1);

```


## 模板初始化

```

```