# 网站构建框架规范（2026-08-25 定稿，全站统一）

> 参考：Polymarket 官网（固定顶栏导航 + 卡片内容 + 面包屑，滚动不跑位）、
> Apple / SAP 风格（浅色 #f5f5f7、白卡、单一强调色 #0071e3、系统字体栈、留白）。
> 原则：全站协调一致，禁止页面间导航/布局/角标不一致。

## 一、统一顶栏导航（所有页面必须有，滚动固定不跑位）

```text
结构（从左到右）：
  [品牌] 弹幕情报库（logo + 文字，点击回首页）
  [链接] 首页 / 今日比赛 / 历史情报库 / 市场链接 / 订阅
行为：position:sticky top:0 + backdrop blur；当前页高亮（accent 色 + 加粗）；
  移动端自动换行不溢出。
样式：白底 rgba(245,245,247,.92)，13px，hover 变 accent；与页面内容同宽
  （max-width 与正文一致，margin auto）。
```

## 二、面包屑（二级及以上页面必含）

```text
格式：首页 › 类目 › 页面标题（当前页加粗，不可点）
  首页（根目录）：无面包屑
  intel/ 列表页：首页 › 历史情报库 / 今日比赛 / 市场链接
  情报页：首页 › 历史情报库 › 比赛标题
  时间轴壳：首页 › 今日比赛 › 比赛标题
行为：类目可点击返回上级；当前页不可点。
```

## 三、角标（favicon，全站必含）

```text
文件：favicon.svg（SAP 蓝渐变弹幕气泡图标，站点根目录）
引用：所有 HTML <head> 内 <link rel="icon" type="image/svg+xml">
  （根目录页 href="favicon.svg"；intel/ 子页 href="../favicon.svg"）
覆盖：本地生成页 + 服务器自动产出页（vps_publish 复制后注入）。
```

## 四、布局与交互统一

```text
1. 容器：max-width 900-1020px 居中，左右 16-18px 内边距；
2. 卡片：白底、1px #e5e5ea 边、16-18px 圆角、14-20px 内边距、卡片间距 12-14px；
3. 字体：-apple-system / PingFang SC；正文 13-14px；标题 22-24px 800；
4. 链接：正文链接 accent 色无下划线；hover 保持同色；
5. 禁止锚点跳转式导航（如 #markets 滚动跳转）：市场等入口一律用独立页 +
   卡片入口，点击不引起页面跳动；
6. 状态/徽章：统一圆角 pill（联赛/状态/结果），颜色与现有规范一致；
7. 移动端：优先单列，网格自动适配（auto-fit），不横向溢出。
```

## 五、页面清单与归属

```text
根目录：index（首页）/ subscribe（订阅）
intel/：today（今日）/ history（历史库）/ market_links（市场链接）/
  profiles（画像）/ verification_traces（痕迹）/ stats（统计）/
  intel_danmu_*（情报页）/ match_*（时间轴壳）
每页必须：顶栏导航 +（二级以上）面包屑 + favicon + 统一卡片布局。
```

## 六、实施与校验

```text
1. 统一 NAV 片段（内联样式，无外部依赖）由 add_site_nav.py 生成并全站
   替换/注入（含生成器内置 nav 同步替换）；
2. favicon 由 add_favicon.py 注入；vps_publish 在复制后运行两者，
   保证服务器自动产出页也带导航 + 角标；
3. 回归校验：tests/ 断言"所有站点页含统一导航 + favicon 引用"；
4. 任何新页面（生成器/服务器产出）必须走同一模板，禁止另起样式。
```
