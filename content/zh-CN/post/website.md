---
title: "网站维护的常用操作"
date: 2021-07-23T10:30:00+08:00
draft: false
tags: ["技术"]
categories: ['技术']
---

为了便于维护，记录一下常用操作，这样就不用每次都到处查了。

<!--more-->

配置文件在 `/etc/nginx/nginx.conf`。

## 添加一个 https 站点

### 修改 nginx 配置文件

配置文件中增加：

```
server {
    listen 443 ssl;
    server_name [name].shadiao.online;

    ssl_certificate /etc/letsencrypt/live/shadiao.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/shadiao.online/privkey.pem;

    ssl_session_timeout 5m;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE:ECDH:AES:HIGH:!NULL:!aNULL:!MD5:!ADH:!RC4;    #加密算法
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;    #安全链接可选的加密协议
    ssl_prefer_server_ciphers on;   #使用服务器端的首选算法

    location / {
        # write something
    }
}

```

修改里面的 `server_name`。

location 部分，静态页面：

```
location / {
    add_header Access-Control-Allow-Origin *;
    root /var/www/...;
    index index.html;
}
```

动态页面：

```
location / {
    proxy_pass http://127.0.0.1:xxxx;
    add_header Access-Control-Allow-Origin *;
}
```

以上完成后，最好加上 http 的自动跳转：

```
server {
    listen 80;
    server_name xxx.shadiao.online;
    
    location / {
        # 重定向https
        return 301 https://$server_name$request_uri;
    }
}
```

重启 nginx 以使新配置生效：

```shell
service nginx restart
```

### 设置域名解析

去设置就行了。

### 手动更新证书

如果需要手动更新 ssl 证书：

```shell
/root/.acme.sh/acme.sh --cron -f
```

## 备份与维护

需要备份的内容：

- 各个站点文件
- nginx 配置文件

目前的站点列表：

- 我中央信息门户
- 博客
- 李华大冒险
- 实用工具集