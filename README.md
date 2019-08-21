# edm

## user store 初始化

```

INSERT INTO `store` (`id`, `name`, `url`, `domain`, `email`, `token`, `hmac`, `timezone`, `sender`, `customer_shop`, `sender_address`, `logo`, `service_email`, `currency`, `site_name`, `store_view_id`, `init`, `source`, `user_id`, `store_create_time`, `create_time`, `update_time`)
VALUES
	(1, 'admin', 'admin.myshopify.com', 'www.admin.com', '', '', '', '(GMT+08:00) Asia/Shanghai', 'admin', '', '', NULL, NULL, NULL, NULL, '111111', 1, 1, 1, '2018-08-15 10:39:16.000000', '2019-07-12 09:53:09.077657', '2019-08-07 17:51:30.943595');



INSERT INTO `user` (`id`, `last_login`, `is_superuser`, `first_name`, `last_name`, `is_staff`, `is_active`, `date_joined`, `username`, `email`, `password`, `code`, `create_time`, `update_time`)
VALUES
	(1, NULL, 0, '', '', 0, 1, '2019-07-12 09:53:09.453778', 'admin', '', 'pbkdf2_sha256$120000$6YoSxUhSYlrw$6bJxEh1+uJVQ8cwm47KIzbwXPpmm3lz0qgQmbMr3yKE=', '111111', '2019-07-12 09:53:09.454534', '2019-08-01 14:42:03.904975');

```


## 模板初始化

```


INSERT INTO `customer_group` (`id`, `uuid`, `title`, `description`, `sents`, `opens`, `clicks`, `open_rate`, `click_rate`, `members`, `relation_info`, `customer_list`, `state`, `store_id`, `create_time`, `update_time`)
VALUES
	(1, '94', 'VIP Customers', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"VIP Customers\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer placed order\",\"relations\":[{\"relation\":\"more than\",\"values\":[\"3\",1],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer total order payment amount\",\"relations\":[{\"relation\":\"is more than\",\"values\":[500],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"Accept Marketings\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:04:30.152421', '2019-08-16 13:38:27.824821'),
	(2, '95', 'New ArrivalsNew Customers', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"New ArrivalsNew Customers\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer sign up time\",\"relations\":[{\"relation\":\"is in the past\",\"values\":[15,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer subscribe time\",\"relations\":[{\"relation\":\"is in the past\",\"values\":[15,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer placed order\",\"relations\":[{\"relation\":\"equals\",\"values\":[\"0\"],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"New ArrivalsNew Customers\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:08:56.527726', '2019-08-16 13:38:27.832379'),
	(3, '96', 'Potential Customers', 'Potential Customers', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"Potential Customers\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer paid order\",\"relations\":[{\"relation\":\"equals\",\"values\":[\"0\"],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer placed order\",\"relations\":[{\"relation\":\"more than\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is in the past\",\"values\":[60,1],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"Accept Marketings\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:09:31.025966', '2019-08-16 13:38:27.839564'),
	(4, '97', 'At Churn-Risk Custome', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"At Churn-Risk Custome\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer placed order\",\"relations\":[{\"relation\":\"more than\",\"values\":[\"1\",1],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer last order created time\",\"relations\":[{\"relation\":\"is between\",\"values\":[30,90],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"At Churn-Risk Custome\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:15:13.429793', '2019-08-16 13:38:27.847500'),
	(5, '98', 'Lapsed Customers', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"Lapsed Customers\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer last order created time\",\"relations\":[{\"relation\":\"is between\",\"values\":[90,100000],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer clicked email\",\"relations\":[{\"relation\":\"equals\",\"values\":[\"0\"],\"unit\":\"days\",\"errorMsg\":\"\"},{\"relation\":\"is over all time\",\"values\":[0,1],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"Lapsed Customers\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:21:33.202815', '2019-08-16 13:38:27.855510'),
	(6, '99', 'Active Customers', '', 0, 0, 0, 0.0000, 0.0000, '0', '{\"relation\":\"&&\",\"group_condition\":[{\"group_name\":\"Active Customers\",\"relation\":\"||\",\"children\":[{\"condition\":\"Customer last order created time\",\"relations\":[{\"relation\":\"is in the past\",\"values\":[30,1],\"unit\":\"days\",\"errorMsg\":\"\"}]},{\"condition\":\"Customer last opened email time\",\"relations\":[{\"relation\":\"is in the past\",\"values\":[30,1],\"unit\":\"days\",\"errorMsg\":\"\"}]}]},{\"group_name\":\"Active Customers\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}]}]}]}', '[]', 1, 1, '2019-08-09 18:25:27.987085', '2019-08-16 13:38:27.861897');

```

## 店铺模板


```
INSERT INTO `email_trigger` (`id`, `customer_list_id`, `title`, `description`, `open_rate`, `click_rate`, `revenue`, `relation_info`, `email_delay`, `customer_list`, `note`, `status`, `is_open`, `draft`, `store_id`, `create_time`, `update_time`)
VALUES
	(1, NULL, 'Cart Abandonment', 'Cart Abandonment', 0.0000, 0.0000, 0.0000, '{\"relation\":\"\",\"group_condition\":[{\"group_name\":\"LAST 60 DAYS PURCAHSE\",\"relation\":\"&&\",\"children\":[{\"condition\":\"Customer last order created time\",\"relations\":[{\"relation\":\"is between\",\"values\":[5,7],\"unit\":\"minutes\",\"errorMsg\":\"\"}],\"lastVal\":\"Customer last order created time is between 5 and 7 minutes ago \"},{\"condition\":\"Customer last order status\",\"relations\":[{\"relation\":\"is unpaid\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}],\"lastVal\":\"Customer last order status is unpaid\"},{\"condition\":\"Customer who accept marketing\",\"relations\":[{\"relation\":\"is true\",\"values\":[30],\"unit\":\"days\",\"errorMsg\":\"\"}],\"lastVal\":\"Customer who accept marketing is true\"}]}]}', '[{\"type\":\"Email\",\"value\":2,\"title\":\"Email\",\"unit\":\"first\",\"icon\":\"icon-youjian\",\"state\":false,\"SubjectText\":\"Did you forget something?\"}]', NULL, '[\"Do not send if the customer if your customer makes a purchase.\"]', 1, 0, 0, 1, '2019-08-19 14:56:14.424154', '2019-08-19 15:10:52.147780');


INSERT INTO `email_template` (`id`, `title`, `description`, `subject`, `heading_text`, `revenue`, `sessions`, `transcations`, `logo`, `banner`, `banner_text`, `headline`, `body_text`, `product_list`, `product_title`, `product_condition`, `customer_group_list`, `send_rule`, `status`, `is_cart`, `enable`, `send_type`, `html`, `store_id`, `create_time`, `update_time`)
VALUES
	(2, NULL, NULL, 'Did you forget something?', 'We are still waiting for you at *[tr_shop_name]*', 0.0000, 0, 0, 'https://smartsend.seamarketings.com/media/1/mfkjn0xvb4lpzg5.jpg', 'https://smartsend.seamarketings.com/media/1/yjzluxova4972kr.jpg', '{\"width\":400,\"left\":15,\"top\":50,\"fontSize\":18,\"textAlign\":\"left\",\"color\":\"#000\",\"border\":\"0px\"}', 'Did you forget something?', 'Dear *[tr_firstname]*, We noticed you left *[tr_firstname]* without completing your order. Don’t worry, we saved your shopping cart so you can easily click back and continue shopping any time.', '[]', 'you may also like', 'top_fifteen', '[]', '{}', 0, 1, 0, 1, '<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no\"><title>jquery</title><style>a:hover{text-decoration: underline!important; }.hide{display:none!important;}</style></head><body><div style=\"width:880px;margin:0 auto;\"><div class=\"showBox\" style=\"overflow-wrap: break-word; text-align: center; font-size: 14px; width: 100%; margin: 0px auto;\"><div style=\"width: 100%; padding: 20px 0px;\"><div style=\"width: 30%; margin: 0px auto;\"><img src=\"https://smartsend.seamarketings.com/media/1/mfkjn0xvb4lpzg5.jpg\" style=\"width: 100%;\"></div></div><div style=\"width: 100%; padding-bottom: 20px; position: relative; overflow: hidden;\"><div class=\"bannerText\" style=\"position: absolute; left: 15px; top: 50px; text-align: left; width: 400px; line-height: 30px; font-size: 18px; color: rgb(0, 0, 0); border: 2px dashed rgb(204, 204, 204);\"><div>\n                                            Did you forget something?\n                                    </div><div>\n                                            We are still waiting for you at *[tr_shop_name]*\n                                    </div><div>\n                                            Did you forget something?\n                                    </div><div>\n                                            Dear *[tr_firstname]*, We noticed you left *[tr_firstname]* without completing your order. Don’t worry, we saved your shopping cart so you can easily click back and continue shopping any time.\n                                    </div></div><div style=\"width: 100%;\"><img src=\"https://smartsend.seamarketings.com/media/1/yjzluxova4972kr.jpg\" style=\"width: 100%;\"></div></div><div style=\"width: 100%; padding-bottom: 20px; position: relative;\"><div style=\"position: absolute; width: 100%; height: 3px; background: rgb(0, 0, 0); top: 40px; left: 0px;\"></div><table border=\"0\" cellspacing=\"0\" style=\"width: calc(100% - 40px); font-weight: 800; margin-left: 20px;\"><thead style=\"padding: 20px 0px; line-height: 50px; border-bottom: 3px solid rgb(221, 221, 221);\"><tr style=\"font-size: 18px; border-bottom: 10px solid rgb(0, 0, 0);\"><td style=\"width: 50%;\">ITEM(S)</td><td>UNIT PRICE</td><td>QUANTITY</td><td>AMOUNT</td></tr></thead><tbody>\n                                        *[tr_cart_products]*\n                                    </tbody></table></div><div style=\"width: 100%; padding-bottom: 20px; text-align: right;\"><a href=\"*[tr_abandoned_checkout_url]*\" style=\"cursor: pointer; color: rgb(255, 255, 255); background: rgb(0, 0, 0); padding: 10px; font-weight: 800; display: inline-block; margin-right: 20px;\">CHECK TO PAY</a></div><div class=\"*[tr_products_title]*\" style=\"width: 100%; padding-bottom: 20px; font-size: 20px; font-weight: 800;\">\n                                you may also like\n                        </div><div style=\"width: calc(100% - 24px); padding: 20px 12px;\">\n                            *[tr_top_products]*\n                        </div><div style=\"width: calc(100% - 24px); padding: 20px 12px; text-align: center;\">\n                        @2006-2019 <a href=\"*[tr_store_url]*\" target=\"_blank\">*[tr_domain]*</a>  Copyright,All Rights Reserved\n                    </div><div style=\"width: calc(100% - 24px); padding: 20px 12px; text-align: center;\"><a href=\"*[link_unsubscribe]*\" target=\"_blank\" style=\"text-decoration: none; cursor: pointer; color: rgb(254, 34, 46); padding: 0px 10px; border-right: 2px solid rgb(204, 204, 204); font-size: 24px;\">UNSUBSCRIBE</a><a href=\"*[tr_help_center_url]*\" target=\"_blank\" style=\"text-decoration: none; cursor: pointer; color: rgb(254, 34, 46); padding: 0px 10px; border-right: 2px solid rgb(204, 204, 204); font-size: 24px;\">HELP CENTER</a><a href=\"*[tr_privacy_policy_url]*\" target=\"_blank\" style=\"text-decoration: none; cursor: pointer; color: rgb(254, 34, 46); padding: 0px 10px; border-right: 2px solid rgb(204, 204, 204); font-size: 24px;\">PRIVACY POLICY</a><a href=\"*[tr_about_us_url]*\" target=\"_blank\" style=\"text-decoration: none; cursor: pointer; color: rgb(254, 34, 46); padding: 0px 10px; font-size: 24px;\">ABOUT US</a></div><div style=\"width: calc(100% - 24px); padding: 20px 12px; text-align: center;\">\n                        This email was sent a notification-only address that cannot accept incoming email PLEASE\n                        DO NOT REPLY to this message. if you have any questions or concerns.please email us:*[tr_service_email]*\n                    </div></div></div></body></html>', 1, '2019-08-19 14:55:59.594417', '2019-08-19 14:55:59.594455');




```