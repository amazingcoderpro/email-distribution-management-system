# -*-coding: utf-8-*-
import multiprocessing
import gevent.monkey
import os

gevent.monkey.patch_all()

# 并行工作进程数
workers = multiprocessing.cpu_count() * 2 + 1
# 每个进程的开启线程
threads = 1
# 监听端口80
bind = '0.0.0.0:8000'
# 设置守护进程,将进程交给supervisor管理
daemon = True
# 开启debug模式
debug = True
# 工作模式协程
worker_class = 'gevent'
# 设置最大并发量
worker_connections = 2000
# 设置进程文件目录
pidfile = '/var/run/gunicorn.pid'
# 设置访问日志和错误信息日志路径
accesslog = '/var/log/gunicorn_acess.log'
errorlog = '/var/log/gunicorn_error.log'
# # 设置日志记录水平
loglevel = 'info'