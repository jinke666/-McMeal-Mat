# 麦麦搭子 (McMeal-Mate) 麦当劳 MCP 集成说明文档

本文档详细阐述 **麦麦搭子 (McMeal-Mate)** 如何接入并深度融合麦当劳中国官方 MCP（Model Context Protocol）服务，涵盖系统架构、调用的 Tool 列表、全链路时序图、实测返回证据与业务价值。

---

## 一、 系统架构与 MCP 拓扑关系

`麦麦搭子` 将大语言模型智能体（麦麦店员人设）、运筹学多约束背包算法、双人协同公平分摊模型与麦当劳官方生产环境 MCP Server 深度打通。

```mermaid
flowchart TD
    User([用户自然语言意图 / 双人点餐]) --> MaiMai[虚拟店员 麦麦 Agent 协调器]
    
    subgraph McMealCore ["McMeal-Mate 核心系统"]
        MaiMai --> Parser[意图解析器<br/>提取双人偏好/热量/忌口]
        Parser --> Optimizer[McOptimizer 运筹求解引擎<br/>双人独立偏好 + 共享小食分离 + 公平分摊]
    end

    subgraph McdMCP ["麦当劳官方 MCP Server (https://mcp.mcd.cn)"]
        T1[list-nutrition-foods<br/>160款全量餐品热量/蛋白质/钠数据]
        T2[campaign-calendar & now-time-info<br/>服务器时间与营销活动日历]
        T3[available-coupons & auto-bind-coupons<br/>麦麦省优惠券查询与一键秒领]
        T4[query-nearby-stores & query-meals<br/>基于 LBS 查询门店及实时在售菜单与'上新'标签]
        T5[calculate-price<br/>官方价格与满减规则真实校验 (分单位)]
        T6[create-order<br/>订单创建与堂食/外带取餐柜二维码]
    end

    MaiMai -->|1. 时间与日历扫描| T2
    MaiMai -->|2. 一键领券同步| T3
    MaiMai -->|3. LBS门店与在售菜单拉取| T4
    MaiMai -->|4. 营养素底层映射| T1
    
    T1 & T3 & T4 --> Optimizer
    Optimizer -->|5. 最优组合真实核价| T5
    T5 -->|6. 最终确认方案| User
    User -.->|用户明确确认| T6
```

---

## 二、 实际调用的麦当劳 MCP Tool 清单与实测证据

| 序号 | MCP Tool 名称 | 工具中文描述 | 实测状态 | 在麦麦搭子中的具体业务价值与实测证据 |
|:---:|:---|:---|:---:|:---|
| 1 | `now-time-info` | 服务器时间查询 | ✅ LIVE_VERIFIED | 实测返回时间戳与 `dayOfWeek: MONDAY`，精准判断正餐/早餐时段及周一会员日。 |
| 2 | `campaign-calendar` | 营销活动日历 | ✅ LIVE_VERIFIED | 自动捕获当月活动日历，将特惠日程纳入目标函数。 |
| 3 | `available-coupons` | 麦麦省优惠券列表 | ✅ LIVE_VERIFIED | 动态识别中薯条买一送一、免费脆薯饼、9.9元冰美式等真实优惠券。 |
| 4 | `auto-bind-coupons` | 麦麦省一键领券 | ✅ LIVE_VERIFIED | 点餐前零点击全自动绑定所有可用券包，解决用户忘记领券痛点。 |
| 5 | `query-nearby-stores` | 查询附近可用门店 | ✅ LIVE_VERIFIED | 实测按位置定位到上海黄浦华旭大厦餐厅（`storeCode: 1450713`）等。 |
| 6 | `query-meals` | 门店在售餐品列表 | ✅ LIVE_VERIFIED | **实测核心证据**：返回完整菜单，餐品直接携带 `"tags": ["上新", "韩式辣椒黄油风味"]`，为**新品发现**提供官方真实数据源！ |
| 7 | `list-nutrition-foods` | 餐品营养成分列表 | ✅ LIVE_VERIFIED | 官方 160 款权威餐品热量 (kcal)、蛋白质、钠、钙全量数据，为健康控卡提供依据。 |
| 8 | `calculate-price` | 商品真实价格核算 | ✅ LIVE_VERIFIED | **实测核心证据**：向官方提交餐品，返回分级金额（单位分）、优惠明细及 `takeWayList`（堂食/外带取餐柜）。 |
| 9 | `delivery-query-stores` | 外送可配送门店 | ✅ LIVE_VERIFIED | 验证外送场景下门店可达性与起送门槛。 |

---

## 三、 双人协同点餐执行时序图 (Duo Workflow)

```mermaid
sequenceDiagram
    autonumber
    actor Alice as 用户 A (小明)
    actor Bob as 用户 B (小红)
    participant MaiMai as 麦麦店员 (Skill / Agent)
    participant MCP as 麦当劳 MCP Server
    participant Opt as McOptimizer (运筹算法)

    Alice->>MaiMai: "我和小红一起吃，预算65元，我爱吃肉微辣，小红不吃辣要冷饮"
    Note over MaiMai: 意图解析: 两人独立偏好 + 忌口分离 + 团队预算
    
    MaiMai->>MCP: auto-bind-coupons() 一键绑定券包
    MCP-->>MaiMai: 领券成功
    
    MaiMai->>MCP: query-nearby-stores("上海", "人民广场")
    MCP-->>MaiMai: 返回最近餐厅 storeCode: 1450713
    
    MaiMai->>MCP: query-meals(storeCode) & list-nutrition-foods()
    MCP-->>MaiMai: 返回实时在售餐品列表 (含'上新'标签) + 官方营养素
    
    MaiMai->>Opt: 求解双人协同方案 (Alice偏好, Bob偏好, 共享小食池)
    Note over Opt: 1. 为 Alice 匹配喜肉微辣汉堡 + 饮品<br/>2. 为 Bob 匹配不吃辣汉堡 + 冷饮<br/>3. 精选共享小食 (买一送一薯条 / 心形薯饼)<br/>4. 应用 1+1 随心配等效替代<br/>5. 执行数学公平分摊算法 (Fair Allocation)
    Opt-->>MaiMai: 产出 3 套双人方案 (最省钱 / 尝鲜探索 / 黄金满足)

    MaiMai->>MCP: calculate-price(items)
    MCP-->>MaiMai: 官方真实算价校验成功 (LIVE_VERIFIED)
    
    MaiMai->>Alice: 汇报麦麦店员语音 + 两人各自餐品 + 精确到角分的 AA 转账单
```

---

## 四、 核心算法与数据真实性规范

### 1. 数据真实性标记 (Data Reliability Standards)
为杜绝大模型在电商点餐场景下的虚构幻觉，系统全量落地四级数据信度标准：
- **`LIVE_VERIFIED`**：本次运行真实调用官方 MCP 接口并返回 200 OK 确认；
- **`CACHED`**：使用本地带时间戳的缓存数据；
- **`ESTIMATED`**：算法本地规划算价与比例估算；
- **`MOCK`**：离线沙箱基准数据。

### 2. 双人公平分摊数学模型 (Fair Cost Splitting)
对于 $N$ 人协同点餐，第 $i$ 位的基准总额为个人餐品原价 $C_i$ 与均摊共享餐品原价 $S/N$ 之和：
$$T_i = C_i + \frac{S}{N}$$
整单享受的全部优惠 $D = \sum T_k - P_{\text{actual}}$ 按基准总额权重科学抵扣：
$$D_i = D \times \frac{T_i}{\sum T_k}$$
最终第 $i$ 位成员应付金额为：
$$P_i = T_i - D_i$$
该模型在博弈论上保证了：**点餐基准额越高的成员享有同比例折扣，且每位成员均能均等分享团队优惠杠杆，谁也不占谁便宜。**
