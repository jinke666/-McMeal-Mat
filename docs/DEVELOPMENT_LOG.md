# 开发记录

> 记录事实，不把计划写成已完成结果。每条记录建议注明日期、负责人、改动、验证方法和结果。

## 2026-10-12：建立跨工具协作迁移草案
- 背景：WorkBuddy 项目页面显示“网络异常，项目暂时无法加载”。
- 已知情况：项目页面当前无法正常加载；具体原因尚未确认。
- 本次准备：建立项目背景、AI 协作规则、任务清单和决策记录模板。
- 尚未验证：
  - 这些文件是否已放入实际仓库；
  - GitHub 是否包含最新代码；
  - WorkBuddy 故障原因；
  - 当前 MCP 连接和项目启动状态。
- 下一步：检查 Git 状态并备份本地内容；由团队确认后再将文档加入仓库。
 
## 2026-10-12：McMeal-Mate 核心系统开发完成与大赛规范交付
- 负责人：keke & 合作者
- 核心进展：
  1. 完成 `mcmeal` 核心包架构设计与实现（`config`, `models`, `mcp_client`, `optimizer`, `agent`, `cli`）；
  2. 实现基于多约束 0-1 背包问题与动态规划的运筹配餐算法，支持随心配 1+1 规则矩阵与单品/满减券深度折抵；
  3. 实现办公室麦乐送 39 元免配送费最优凑单算法 (`optimize_delivery_pooling`)；
  4. 接入麦当劳官方 160 款权威餐品全量营养素数据库（`list-nutrition-foods`），支持卡路里与宏量营养素管控；
  5. 编写 6 项全链路自动化单元测试，100% 通过；
  6. 严格按大赛官方规范产出 5 大必备文件：`README.md`、`CONTEST_DECLARATION.md`、`MCP_INTEGRATION.md`、`mcp-config.example.json`、`workbuddy.md`；
  7. 配置 GitHub Actions CI 工作流，保障跨平台版本自动化测试。
- 验证方式：`python -m unittest discover -s tests -v`（6/6 OK）；`python scripts/demo.py`（三大场景运行正常）。

## 2026-10-12：升级为“麦麦搭子”v1.0 (双人协同点餐 + 公平分摊 + SKILL 规范)
- 负责人：keke & 合作者
- 核心进展：
  1. **产品定位重塑**：针对榜单前 40 名中单人省钱工具严重同质化痛点，重构为“麦麦搭子”，主打双人/多人协同点餐与公平分摊算法；
  2. **双人运筹算法与模型升级**：在 `models.py` 与 `optimizer.py` 中引入 `MemberPreference`, `MemberShare`, `GroupOrderPlan`，实现了独立餐品忌口隔离与共享小食按比例公平减免的数学模型；
  3. **官方上新标签动态识别**：`mcp_client.py` 动态解析 `query-meals` 返回中的 `"tags": ["上新"]` 属性，提供可实证的尝鲜推荐；
  4. **标准 Agent SKILL 规范发布**：创建根目录 `SKILL.md`，定义虚拟店员“麦麦”人设、执行铁律及触发时机；
  5. **严格数据可信标准落地**：建立 `LIVE_VERIFIED`、`CACHED`、`ESTIMATED`、`MOCK` 标识体系，打通真实算价接口 `calculate-price`；
  6. **文档与演示矩阵更新**：全面重构 `README.md`、`workbuddy.md`、`MCP_INTEGRATION.md`、`TASKS.md`，并在 `cli.py` 与 `scripts/demo.py` 中加入双人协同场景。
- 验证方式：全量单元测试 7/7 通过；运行 `python -m mcmeal.cli --duo` 与 `python scripts/demo.py` 验证双人方案与账单。


