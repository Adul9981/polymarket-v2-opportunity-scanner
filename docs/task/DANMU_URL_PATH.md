# 弹幕情报台公开访问路径

更新时间：2026-11-24

## 用户入口

服务器直连统一使用：

```text
http://158.247.214.175/danmu/
```

旧入口：

```text
http://158.247.214.175/
http://158.247.214.175/index.html
```

两者均永久跳转到 `/danmu/`，避免用户继续看到 `index.html`。

GitHub Pages 镜像：

```text
https://adul9981.github.io/danmu-intel/
```

## 实现

- nginx 配置片段：`deploy/nginx/danmu-path.conf`；
- 服务器安装位置：`/etc/nginx/snippets/danmu-path.conf`；
- `/var/www/danmu` 指向 `/var/www/danmu-pulse`；
- 站点继续使用相对路径，因此 `/danmu/intel/...`、助手资源和赛前详情无需改写；
- `/alpha/` 与 `/intel/api/` 等专用 location 不受影响。

## 域名边界

`danmupulse.com` 目前 DNS 未指向当前 VPS，443 端口也未启用。若后续切 DNS：

1. A 记录指向 `158.247.214.175`；
2. 配置 HTTPS 证书；
3. 再决定是否把根域名直接映射到 `/danmu/`。

在 DNS 未切换前，不把该域名作为公开入口。
