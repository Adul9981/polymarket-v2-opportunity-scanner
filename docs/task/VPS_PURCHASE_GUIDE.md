# 云服务器购买与开通教程（弹幕采集 + Codex 上云用）

> 2026-08-24 编写。目标：买一台 2核 / 4GB / 80GB SSD 的云服务器，
> 先跑弹幕采集（7×24），跑稳后再装 Codex CLI 实现全自动。
> 配套方案见 SERVER_CODEX_PLAN.md，部署交接见 VPS_HANDOFF.md。

---

## 0. 平台选择：首选 Vultr，备选 DigitalOcean

| 对比项 | Vultr（推荐） | DigitalOcean |
| --- | --- | --- |
| 2核/4GB/80GB 月费 | 约 $20–24（按所选系列） | $24（Basic） |
| 支付方式 | 支付宝 / 银联 / PayPal / 信用卡 | 仅信用卡 / PayPal（新账号常有卡验证） |
| 亚洲节点 | 东京 / 首尔 / 新加坡 / 悉尼 | 亚洲只有新加坡 |
| 计费 | 按小时，删除实例立即停止扣费 | 按秒计费（2026 年起），删除停止扣费 |
| 上手难度 | 低 | 低 |

两个关键结论：

1. **用支付宝就选 Vultr**。DigitalOcean 不收支付宝，新账号还可能要求信用卡预授权验证，对新手不友好。
2. **节点选东京，不要找"香港"**。Vultr 和 DigitalOcean 都没有香港机房；
   方案文档里"香港或东京"的说法落到这两家平台上，实际可选的最优解是东京
   （访问虎牙直播、OpenAI、Polymarket 都通畅）。国内云厂商的香港节点
   需要实名且多为大陆线路优化，不是本场景首选。

> 价格为 2026-08 搜索核实的参考值（Vultr Regular 2C/4G 约 $20/月、
> High Frequency 约 $24/月；DO Basic 2C/4G/80GB $24/月），下单时以官网实时页面为准。

---

## 1. 注册 Vultr 账号

1. 浏览器打开 `vultr.com`，点右上角 **Register**。
2. 填邮箱 + 密码。密码要求至少 10 位，且包含大写字母、小写字母、数字、特殊字符中的至少三种。
3. 点 **Create Account** 后，去邮箱找 "Welcome to Vultr.com" 邮件，点里面的验证链接。
   （收件箱没有就看垃圾邮件文件夹；不验证邮箱无法进入充值页面。）

## 2. 支付宝充值

1. 登录后进入 **Billing → Make a Payment**（新用户验证邮箱后通常会自动引导到这里）。
2. 支付方式选 **Alipay**。
3. 账单信息按**拼音**填写（这是最容易卡住的一步，报 "Please make sure you fill out all Address fields" 就是没填全）：
   - Your Name：姓名拼音，如 `Zhang San`
   - Billing Address：区县拼音，如 `Chaoyang Qu`
   - Billing City：城市拼音，如 `Beijing`
   - Country/Region：选 `China`
   - Postal Code：当地邮编
4. 金额建议 **$25**（覆盖首月 $20–24 + 少量缓冲；Vultr 充值一般有最低 $10 限制）。
5. 跳转支付宝扫码付款，回到 Vultr 看到余额到账即成功。

> 注意：部分"新用户赠金"活动不支持支付宝通道，遇提示换信用卡/ PayPal 属正常，
> 不影响按原价充值使用。

## 3. 创建服务器（核心步骤）

1. 左侧菜单 **Products → 右上角 Deploy New Server**（或 "+" 按钮）。
2. **Choose Type**：选 **Cloud Compute**。
   - 系列选 **Regular Cloud Compute**（便宜，够用）；
   - 想性能更好可选 **High Frequency**，同配置约贵 $4/月。
3. **Choose Location**：选 **Tokyo**。
   （备选：Seoul / Singapore。不要选 IPv6 Only 的特价机，没有公网 IPv4。）
4. **Choose Image**：**Ubuntu 24.04 LTS x64**。
   （Codex CLI 官方支持 Ubuntu 20.04+，24.04 LTS 一步到位。）
5. **Choose Plan**：选 **2 vCPU / 4 GB RAM / 80 GB SSD** 那一档。
   页面会实时显示月费（约 $20–24），确认后再继续。
6. **附加项**：
   - Automated Backups：**不勾**（备份我们自己做，省约 20% 月费）。
   - IPv6：默认带，不用动。
7. **SSH Keys**：第一次买可以先跳过——Vultr 会在控制台生成 root 密码，
   够用；等朋友部署时再补密钥更规范（见第 6 步）。
8. **Hostname**：填 `polymarket-danmu`（只是机器名，随意）。
9. 点 **Deploy Now**。

## 4. 获取连接信息

1. 等 1–2 分钟，实例状态变为 **Running**。
2. 点进该实例，在 **Overview** 页记下四样东西：
   - IP Address（公网 IP）
   - 用户名：`root`
   - Password（控制台里那串，点眼睛图标显示）
   - 端口：`22`（默认）
3. 这四样先保存在自己本地（别发群、别上公开仓库）。

## 5. 本机测试连接（Mac 自带终端即可）

```bash
ssh root@<服务器IP>
```

- 第一次连接提示 `Are you sure you want to continue connecting (yes/no)?`，输入 `yes` 回车。
- 粘贴密码（输入时屏幕不显示任何字符，是正常的），回车。
- 登录成功后跑三条命令自检：

```bash
uname -a     # 确认是 Ubuntu 24.04
free -h      # 内存应约 4GB
df -h        # 系统盘应约 80GB
```

能跑通，这台机器就"开通"完毕了。

## 6. 交给朋友部署（安全做法）

推荐顺序（安全性从高到低）：

1. **密钥优先**：让朋友把他的 SSH 公钥发给你，你在服务器上执行
   `echo "<公钥内容>" >> /root/.ssh/authorized_keys`，之后他用密钥登录，全程不给密码。
2. **给一次性密码**：如果朋友坚持用密码，把第 4 步的 root 密码通过私聊给他；
   **部署完成后必须立刻**：改 root 密码 + 关闭密码登录（只留密钥登录）。
3. root 权限给到"能装软件、能建 systemd 服务"即可，不需要其他授权。

朋友部署的内容按 `docs/task/VPS_HANDOFF.md` 的部署包执行：
弹幕采集服务（deploy.sh + danmu-session.service）→ 跑稳后再装 Codex CLI
（Codex 首次 OAuth 登录需要你本人操作，朋友代替不了）。

## 7. 常见坑

- **计费**：按小时计费，只要实例存在就扣费；不想用了要 **Destroy**（销毁）才停扣，"关机"（Stop）在 Vultr 仍保留资源位。
- **IP 问题**：个别新 IP 访问某些站点异常，删掉实例重建即得新 IP，成本为零。
- **别买错系列**：$2.5/月 那档是 IPv6 Only，无公网 IPv4，SSH 都不好连，跳过。
- **流量**：月费含 3–4TB 出站流量，弹幕采集 + 情报页完全够用，超出部分 $0.01/GB。

## 8. 买完告诉我什么

下单并测试连接成功后，把这些发给我（本窗口）：

1. 服务器 IP、SSH 端口（默认 22 就说默认）；
2. 操作系统确认（Ubuntu 24.04）；
3. 是否已加朋友的公钥。

我这边随即准备好：采集部署包复核、双 Codex 交接协议落文档、
以及"服务器采集 → 本地分析"的定时拉取任务。
