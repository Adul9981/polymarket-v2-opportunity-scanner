# 订阅 API（参考马斯克工具实现）

两个 Vercel serverless 函数，与 musk-tweet-quant-v2 同款模式：

```text
/api/verify-member  会员验证：POST {identifier: "TG用户名 或 QQ号"}
                    -> {member, freePeriod, plan, expires}
/api/lead          订阅登记：POST {name, contact, note} -> 推送到站长 Telegram
```

## 部署（Vercel）

```bash
cd <本仓库根目录>（含 api/ + vercel.json）
vercel --prod
```

环境变量（Vercel 项目设置）：

```text
FREE_UNTIL              免费体验期截止（默认 2026-08-31T23:59:59+08:00）
MEMBERS_GIST_RAW_URL    会员名单私有 raw JSON 地址
                        （格式见 data/members.example.json）
TELEGRAM_BOT_TOKEN      站长 Telegram Bot Token（/api/lead 推送用）
TELEGRAM_CHAT_ID        站长 Telegram Chat ID
```

## 名单维护（会员发放）

用户提供 QQ 号或 TG 用户名 -> 登记进名单（私有 Gist 或私有 raw JSON）：

```json
{ "updated_at": "2026-08-24",
  "members": [
    { "tg": "@user", "id": "123456", "plan": "monthly", "expires": "2026-09-24T23:59:59+08:00" }
  ] }
```

expires 到期后自动失效；续费 = 更新 expires。

## 防错：跨域 API 必须处理 OPTIONS 预检（2026-08-25 固化）

```text
教训：verify-member / lead / track 曾只处理 POST，浏览器从站点（GitHub Pages /
自定义域名）跨域调 API 时 OPTIONS 预检返回 405 -> 前端报"验证服务暂不可用"，
但 curl 直测（无浏览器预检）全部成功，极易漏检。
规则：所有被浏览器直接调用的 API（verify-member / lead / track 等）必须：
  1) 设置 Access-Control-Allow-Origin: *；
  2) 处理 OPTIONS：返回 204 + Allow-Methods(POST,OPTIONS) + Allow-Headers(Content-Type)；
  3) 上线后必须模拟浏览器预检：curl -X OPTIONS 带 Origin/Request-Method 头，
     确认 204 后再算可用。
```
