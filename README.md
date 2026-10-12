<p align="center">
  <h1 align="center">🍔 麦麦搭子 McMeal-Mate</h1>
  <p align="center">
    <strong>会记住你的口味、主动发现新品、核对优惠并陪你和朋友一起点餐的 AI 虚拟店员 Skill</strong>
  </p>
  <p align="center">
    <i>“用运筹学吃透麦当劳，多人点餐不纠结，让每一分预算都花在刀刃上！”</i>
  </p>
  <p align="center">
    <a href="#-核心亮点"><img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python Version"></a>
    <a href="#-参赛说明"><img src="https://img.shields.io/badge/McDonald's-1024_Challenge-FFC72C.svg" alt="1024 Challenge"></a>
    <a href="#-规范标准"><img src="https://img.shields.io/badge/Skill-Agent_Specification-purple.svg" alt="Skill Standard"></a>
    <a href="#-算法架构"><img src="https://img.shields.io/badge/Algorithm-Fair_Splitting_%26_Knapsack-orange.svg" alt="Algorithm"></a>
    <a href="#-mcp-能力"><img src="https://img.shields.io/badge/MCP-Streamable_HTTP-green.svg" alt="MCP"></a>
  </p>
</p>

---

## 📖 项目简介 (Introduction)

在麦当劳点餐时，你是否经常遇到这些困扰？
- **优惠规则复杂碎片**：1+1 随心配、麦麦省立减券、买一送一券、会员日日历、满减券……普通用户算不清组合，经常被“反向凑单”；
- **多人/双人拼单算账头秃**：同事或情侣一起点餐，“一个吃辣一个不吃辣，他有5元券我有免配券”，共享小食怎么摊？最终怎么算才公平、谁也不占谁便宜？
- **想尝新品却怕踩雷**：菜单里不知道哪些是真正当季上新，缺少可验证的官方新品推荐；
- **久坐程序员身材管理**：想吃快餐又怕爆卡路里，想要高蛋白、低碳水搭配却查不到精确营养比例。

**麦麦搭子 (McMeal-Mate)** 诞生于 2026 年麦当劳 1024 程序员创意开发大赛。它是一个有活人感、认真诚实的虚拟店员 **Skill**，不仅具备运筹学多约束背包算法（Knapsack Problem）与麦当劳官方 MCP 数据服务，更独创了**双人协同点餐与数学公平分摊算法 (Fair Cost Allocation)**，实现**全自动资产同步、双人口味撮合、共享小食拆分、上新发现与官方闭环核价**。

---

## ✨ 核心亮点 (Key Highlights)

- 👥 **双人/多人协同点餐与公平分摊 (核心差异化)**：
  - 独立输入并满足双方的口味、忌口（如一人吃辣一人不吃辣、一人要热饮）；
  - 自动优选双方都能接受的**团队共享小食**（如买一送一中薯条、小食盒）；
  - **数学级公平分摊算法**：共享小食人均等额平摊，整单优惠与满减按个人基准原价权重科学抵扣，生成精准到角分的 AA 微信转账账单！
- 🧮 **硬核运筹学背包优化引擎**：
  将配餐抽象为**多约束 0-1 背包问题与动态规划模型**，自动识别随心配 1+1（红区+白区 13.9 元）等效代换，穷尽单品券与满减券最优解，常态化砍出 **2.8 折 ~ 4.5 折** 极致优惠！
- 🆕 **基于官方实时标签的新品发现 (Verifiable New Arrivals)**：
  对接真实 `query-meals` 接口，自动捕获官方携带 `"tags": ["上新"]` 的当季新品（如龙焰鸡腿堡、月下相思扭扭薯），让用户尝鲜有据可查。
- 🤝 **免外送费最优凑单算法 (Delivery Pooling)**：
  面对 39 元免配门槛，算法毫秒级计算最优填补餐品，将溢出浪费金额控制在 **1 元以内**。
- 🥗 **极客控卡与宏量营养把关**：
  接入官方 `list-nutrition-foods` 160 款权威数据库，精准统计热量（kcal）、蛋白质、脂肪、碳水、钠等指标。
- ⚡ **麦当劳官方 MCP 深度协同**：
  零点击自动调用 `auto-bind-coupons` 领券、`campaign-calendar` 查活动、`query-nearby-stores` 选店、`calculate-price` 真实核价（返回 `LIVE_VERIFIED` 状态）。

---

## 🛠️ 系统架构与 Skill 双层设计 (Architecture)

麦麦搭子采用符合 Agent 生态标准的双层设计：

```mermaid
graph TD
    User([用户自然语言意图 / 双人拼单]) --> MaiMai[虚拟店员 麦麦 Skill 入口 (SKILL.md)]
    
    subgraph AgentSkill ["Agent Skill 协调层"]
        MaiMai --> Parser[意图与双人偏好解析器]
        Parser --> Memory[长期记忆与偏好管理 (用户告知 vs 系统推测)]
    end

    subgraph CoreEngine ["McMeal-Mate 运筹算法引擎"]
        Parser --> Optimizer[McOptimizer 运筹求解引擎]
        Optimizer --> Knapsack["单人多约束背包算法 (Knapsack DP)"]
        Optimizer --> DuoPlanner["双人协同推荐 + 共享小食分离"]
        Optimizer --> FairSplit["数学级公平分摊算法 (Fair Allocation)"]
        Optimizer --> DeliveryPool["免外送费 39 元卡位凑单算法"]
    end

    subgraph MCP ["麦当劳官方 MCP 服务 (https://mcp.mcd.cn)"]
        MaiMai --> M1[now-time-info & campaign-calendar 时间/日历]
        MaiMai --> M2[auto-bind-coupons 一键秒领优惠券]
        MaiMai --> M3[query-nearby-stores & query-meals 门店与在售菜单]
        MaiMai --> M4[list-nutrition-foods 官方 160 款营养库]
        Optimizer --> M5[calculate-price 官方真实验算 (LIVE_VERIFIED)]
    end

    M1 & M2 & M3 & M4 --> Optimizer
    Optimizer --> Report[高颜值推荐报告: 最省钱双人餐 / 尝鲜探索餐 / 黄金满足餐]
    Report --> User
```

---

## 🚀 快速上手 (Quick Start)

### 1. 克隆代码

```bash
git clone https://github.com/jinke666/-McMeal-Mat.git
cd -McMeal-Mat
```

### 2. 运行环境配置 (可选)

本项目核心算法使用 Python 3.9+ 标准库开发，无强制三方依赖。若接入麦当劳真实远程 MCP，可配置环境变量：

```bash
# Windows PowerShell
$env:MCD_MCP_TOKEN="YOUR_MCD_MCP_TOKEN"

# Linux / macOS
export MCD_MCP_TOKEN="YOUR_MCD_MCP_TOKEN"
```
> 💡 *注：若未配置 Token，系统会自动转入内置离线高仿真沙箱数据，单测与算法功能 100% 可用。*

### 3. 一键体验演示模式

```bash
# 运行四大典型生活场景演示 (含单人、控卡、免配凑单、双人协同点餐)
python scripts/demo.py
```

### 4. 命令行交互 (CLI)

```bash
# 场景 1：双人协同点餐与精准分摊账单 (核心差异化功能)
python -m mcmeal.cli --duo

# 场景 2：单人 25 元预算极限省钱配餐
python -m mcmeal.cli -b 25 -p "预算 25 元想吃汉堡和可乐"

# 场景 3：办公室麦乐送免外送费 39 元最优凑单算法
python -m mcmeal.cli --pool
```

---

## 📊 终端运行效果演示 (CLI Preview)

### 双人协同点餐与精准分摊效果：

```text
==================================================================
  🍔  McMeal-Mate (麦膳精算师) —— 麦门运筹学算法配餐系统  🍔
       基于多约束背包算法与麦当劳 MCP 的极致省钱决策 Agent
==================================================================

>>> 演示模式：双人协同点餐与公平分摊 (符合 v1.0 规格书 2.2 节) <<<
🤖 麦麦店员: 找到适合你们 2 人的神仙吃法啦！独立餐品满足各自忌口，共享小食按比例公平分摊，谁也不吃亏～ 🎉
📍 匹配餐厅: 麦当劳上海黄浦华旭国际大厦餐厅 (南京东路街道西藏中路336号)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🥇【最省钱双人餐】(Lowest Cost)  [LIVE_VERIFIED]
 💡 充分利用 1+1 随心配与麦麦省买一送一优惠券，人均实付仅需十多元，极致省钱！
─────────────────────────────────────────────────────────────
  🍿 团队共享餐品：
    • 中薯条              单价: ¥14.5

  👥 个人餐品与精准分摊账单（公平数学模型）：
   ┌─ 👤 小明(喜肉/可吃辣):
   │  • 双层吉士汉堡           单价: ¥23.5
   │  • 可乐中杯             单价: ¥10.0
   │  💰 个人原价: ¥33.5 + 共享分摊: ¥7.2 - 优惠分摊: ¥26.9
   │  ➡️  最终应付转账: ¥13.9  (立省: ¥26.9)
   └─ 🥗 个人摄入: 720 kcal | 蛋白质: 29g
   ┌─ 👤 小红(不吃辣/要冷饮):
   │  • 双层吉士汉堡           单价: ¥23.5
   │  • 可乐中杯             单价: ¥10.0
   │  💰 个人原价: ¥33.5 + 共享分摊: ¥7.2 - 优惠分摊: ¥26.9
   │  ➡️  最终应付转账: ¥13.9  (立省: ¥26.9)
   └─ 🥗 个人摄入: 720 kcal | 蛋白质: 29g
─────────────────────────────────────────────────────────────
  💰 整单原价: ¥81.5   ➡️  整单实付: ¥27.8   👥 人均实付: ¥13.9   🎉 全员立省: ¥53.7
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🎯 目标用户群体 (Target Audience)

1. **写字楼拼单同事与情侣好友**：告别谁多付、谁占便宜的尴尬，一键生成公平到角分的 AA 账单；
2. **精打细算的麦门信徒 & 学生党**：在有限预算内追求极致性价比，用算法挖掘隐藏神价；
3. **尝鲜探索派**：实时追踪官方上新标签，第一时间试吃最新餐品；
4. **久坐/健身/身材管控的开发者**：利用麦当劳权威营养库，科学平衡卡路里与蛋白质配比。

---

## 🧪 单元测试 (Testing)

本项目包含完备的自动化单测，覆盖模型数据结构、单人多约束背包、双人协同分摊与免配凑单：

```bash
python -m unittest discover -s tests -v
```

测试执行结果：
```text
test_coupon_properties (test_models.TestModels.test_coupon_properties) ... ok
test_menu_item_defaults (test_models.TestModels.test_menu_item_defaults) ... ok
test_nutrition_addition (test_models.TestModels.test_nutrition_addition) ... ok
test_solve_budget_constraint (test_optimizer.TestOptimizer.test_solve_budget_constraint) ... ok
test_solve_calorie_constraint (test_optimizer.TestOptimizer.test_solve_calorie_constraint) ... ok
test_solve_delivery_pooling (test_optimizer.TestOptimizer.test_solve_delivery_pooling) ... ok
test_solve_group_order (test_optimizer.TestOptimizer.test_solve_group_order) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.009s

OK
```

---

## 📋 大赛规范文件索引 (Contest Compliance)

本项目严格遵守麦当劳程序员创意开发大赛要求，包含以下规范文件：

- [SKILL.md](./SKILL.md) —— **麦麦搭子 Agent Skill 标准定义与人设工作流规范**
- [CONTEST_DECLARATION.md](./CONTEST_DECLARATION.md) —— 原创性、合规性与信息安全参赛声明
- [MCP_INTEGRATION.md](./MCP_INTEGRATION.md) —— 麦当劳 MCP Server 详细集成说明、工具清单与时序图
- [mcp-config.example.json](./mcp-config.example.json) —— 脱敏后的标准 MCP 配置文件
- [workbuddy.md](./workbuddy.md) —— 腾讯 WorkBuddy 智能体联动与上下文记录
- [README.md](./README.md) —— 项目介绍、安装方法、使用示例与目标用户

---

## 🤝 贡献与致谢

- 感谢 **麦当劳中国 (M-China)** 开放功能强大的 MCP 服务；
- 感谢 **腾讯 WorkBuddy** 提供的智能体开发与连接器支持。

⭐ **如果你觉得麦麦搭子实用又贴心，请为我们点亮右上角的 Star！麦门！🙏**