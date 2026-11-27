# 全站导航收敛与搜索（P0-3）

状态：已完成
所属路线：`SITE_OPTIMIZATION_ROADMAP_2026-11-27.md`（P0-3）

## 交付

- 顶部入口按用户确认后的业务顺序整理为：

```text
今日情报
比赛局势
历史库
赛前情报
FAQ
形态决策台
形态图谱
访问统计
搜索
```

- 全公开模式下不显示订阅入口；关闭全公开模式后自动恢复。
- 地图战绩和验证闭环不进入主导航。
- 首页、历史比赛节点和情报详情仍在面包屑中保持上级入口。
- 新增 `search.html` + `search_index.json`：
  - 支持比赛、节点、画像、页面四类；
  - 支持队伍、选手、联赛、日期和中英文关键词；
  - 本地索引约 890 条、线上完整站点约 3,059 条，空查询按类型优先展示；
  - `T1` 实测返回 15 条（索引数量随比赛批次变化）。
- 移动端导航自动换行，不再把尾部的访问统计/搜索入口隐藏在横向滚动区。

## 实现位置

- 导航：`tools/add_site_nav.py`
- 搜索页生成：`tools/build_site_search.py`
- 发布接线：`tools/vps_publish.py`、`tools/publish_intel_pages.py`
- 回归：`tests/test_add_site_nav.py`、`tests/test_site_search.py`、
  `tests/test_site_framework.py`、`tests/test_situation_page.py`

## 验收

- 导航、搜索、面包屑、移动端和站点框架回归 51 项通过；
- 所有页面保持唯一导航、唯一面包屑和 favicon；
- 用户点名的全部入口均有稳定位置，地图战绩和验证闭环不再占据主导航；
- 搜索页无运行时错误。
