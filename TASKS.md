# 麦麦搭子任务看板 (Task Board)

> 维护约定：严格按照《麦麦搭子产品规划与技术方案设计书 (v1.0)》追踪开发进度与任务状态。

## 当前状态
- **项目阶段**：已完成 McMeal-Mate v1.0 P0 核心里程碑（双人协同点餐、公平分摊算法、实时官方上新标签识别、SKILL.md 规范体系与真实算价核验）
- **代码状态**：本地全量单元测试 100% 通过（7/7 通过），CLI 与全流程 Demo 运行顺畅
- **官方 MCP 连接**：已成功实测调用全部关键接口（`now-time-info`, `available-coupons`, `list-nutrition-foods`, `query-nearby-stores`, `query-meals`, `calculate-price`, `delivery-query-addresses`）
- **比赛规则与截止时间**：2026年10月9日 - 10月25日 23:59 截止，按 GitHub Star 排序前 100 名获奖

---

## 阶段规划与交付清单

### P0：双人协同与核心规范 (已全部完成 ✅)
- [x] **定义 SKILL.md 规范体系**：明确虚拟店员“麦麦”人设与执行铁律，定义单人/双人/凑单技能触发规则
- [x] **双人/多人协同点餐建模**：在 `mcmeal/models.py` 中新增 `MemberPreference`, `MemberShare`, `GroupOrderPlan`
- [x] **实现公平分摊数学算法**：在 `mcmeal/optimizer.py` 中实现独立餐品防串味、共享小食按比例公平减免
- [x] **官方上新标签动态识别**：`mcp_client.py` 动态解析 `query-meals` 中的 `"tags": ["上新"]` 属性并展示
- [x] **数据可信分级体系**：定义 `LIVE_VERIFIED`, `CACHED`, `ESTIMATED`, `MOCK` 严格数据标识
- [x] **更新 README.md 与 MCP_INTEGRATION.md**：补充真实接口交互证据链、分摊公式与时序图
- [x] **单元测试验证**：`tests/test_optimizer.py` 新增双人协同与分摊测试用例，100% 通过

### P1：用户记忆与智能偏好 (进行中 🚀)
- [x] 建立轻量级 SQLite 记忆持久化机制 (`mcmeal/memory.py`)
- [x] 标记“用户明确表达 (user-stated)”与“系统推断 (system-inferred)”
- [x] 提供透明查看与随时清除记忆的功能（尊重用户隐私与数据安全）
- [x] 与 Agent 点餐流程联动（自动读取常用偏好、排除历史忌口）

### P2：外送拼单与多渠道扩展 (已就绪 ✅)
- [x] 麦乐送 39 元免外送费最优凑单算法 (`optimize_delivery_pooling`)
- [x] 接入营养成分数据库 (`list-nutrition-foods`) 160 款餐品卡路里与宏量营养素管控
- [x] 命令行高颜值双人模式 (`python -m mcmeal.cli --duo`)
- [x] 场景演示脚本完整呈现 (`python scripts/demo.py`)

### P3：大赛正式提交与发布 (待触发 ⏳)
- [ ] 确保仓库在 10月25日 23:59 前切换为 Public 公开状态
- [ ] 按照大赛官方 Issue 模板在 `M-China/mcd-developer-innovation-challenge` 提交项目 Issue
- [ ] 邀请社区与团队成员体验并点亮 Star
