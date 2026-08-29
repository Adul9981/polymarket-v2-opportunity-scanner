# 香港服务器购买与部署手把手（Vultr 香港，2026-08-24）

> 用途：把"弹幕采集"放到 7×24 云服务器，本地做分析（临时过渡方案）。
> 为什么是 Vultr 香港：DigitalOcean 没有香港节点（亚太仅新加坡/班加罗尔）；
>   Vultr 有香港节点（HKG），操作和 DigitalOcean 一样简单，
>   香港访问虎牙（采集）+ Polymarket（未来读取行情）+ OpenAI（Codex）都顺畅。
> 预算：约 $24/月（4GB 档，以官网页面为准）。耗时：首次约 30-60 分钟。
> 如果朋友帮忙部署，把本文件 + 部署包（deliverables/danmu_intel_vps_deploy.zip）一起发给他即可。

## 第 0 步：准备两样东西

```text
1. 一个常用邮箱（注册 DigitalOcean 用）；
2. 一张能付款的卡（Visa / Mastercard 信用卡或借记卡，或 PayPal）。
```

## 第 1 步：注册 Vultr 账号

```text
1. 浏览器打开 https://www.vultr.com
2. 右上角点 Sign Up（注册），填邮箱 + 设置密码
3. 去邮箱收验证邮件，点确认链接
4. 登录后按提示添加付款方式：信用卡 / PayPal（以页面支持的为准；
   新账户常有试用额度，以官网活动为准，没有就跳过）
```

## 第 2 步：创建服务器（Instance）

```text
1. 登录后点 Deploy → New Server（部署新服务器）
2. Choose Server Location（区域）：选 Hong Kong（香港，HKG）
3. Choose Server Type（系统）：选 Ubuntu → Ubuntu 22.04 LTS x64
4. Choose Server Size（套餐）：选 4GB / 2 vCPUs / 80GB SSD 档
   （约 $24/月；如果档位名称略有不同，认准"4GB / 2 vCPU / 80GB SSD"）
5. SSH Keys（可选）：可以不加，跳过
6. Server Hostname & Label（服务器名字）：填 danmu-intel
7. 点 Deploy Now 按钮
8. 等 1-3 分钟，页面出现服务器 IP；如果没配 SSH key，
   root 密码会显示在服务器详情页或发到你邮箱——抄下来存好
```

## 第 3 步：连上服务器（Mac 终端）

```text
1. Mac 按 Command + 空格，搜索"终端"（Terminal）并打开
2. 输入：ssh root@你的IP     （把"你的IP"换成服务器那串数字）
3. 第一次连接会问 Are you sure...? 输入 yes 回车
4. 输入 root 密码（输入时屏幕不显示，正常，输完回车）
5. 成功标志：命令行提示符变成 root@danmu-intel:~#
```

## 第 4 步：上传部署包 + 一键部署

本机终端（新开一个窗口）执行：

```bash
scp /Users/ad/Documents/polymarket/deliverables/danmu_intel_vps_deploy.zip root@你的IP:/opt/
```

回到已登录服务器的窗口执行：

```bash
cd /opt
unzip danmu_intel_vps_deploy.zip
mv danmu_intel_vps_deploy danmu-intel
cd /opt/danmu-intel
chmod +x deploy.sh
./deploy.sh
```

看到 `deployed（过渡方案：仅采集常驻）` 即部署成功。

## 第 5 步：确认采集在跑

```bash
systemctl status danmu-session.service
```

看到 `active (running)` 绿色状态 = 正常。

```bash
tail -20 /opt/danmu-intel/logs/danmu-session.log
```

等有比赛直播时，检查弹幕文件是否生成：

```bash
find /opt/danmu-intel/docs/data/danmu -name "*.jsonl"
```

## 第 6 步：本地拉数据（每天 / 比赛后拉一次）

本机终端执行：

```bash
scp -r root@你的IP:/opt/danmu-intel/docs/data/danmu/* \
  /Users/ad/Documents/polymarket/docs/data/danmu/
```

> 想更顺（免密码、内网直连）可配 Tailscale，之后我帮你弄。

> 香港节点访问 Polymarket 没有问题（Polymarket 限制的是美国等地区用户）；
> 虎牙采集也已按香港节点设计（部署包内直播间接入逻辑与区域无关）。

## 第 7 步（可选，第二阶段）：在服务器上装 Codex

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex
```

第一次运行选 **Sign in with ChatGPT**，按提示在浏览器登录你的 ChatGPT 账号完成授权
（这步必须你本人做，朋友代替不了）。

## 注意事项

```text
1. 密码只给短期使用：给朋友部署可以给密码，部署完成后改掉或在 DigitalOcean
   面板里改成 SSH 密钥登录，长期别用密码。
2. 账单：4GB 档约 $24/月；不用了的服务器记得删掉（Destroy），避免继续扣费。
3. 出问题先看日志：/opt/danmu-intel/logs/danmu-session.{log,err}
4. 部署完成后把 IP 和登录方式告诉本地 Agent，后续数据同步与分析我来接。
```
