# 麦麦搭子 McMeal-Mate

面向麦当劳点餐场景的 AI Skill。根据预算、口味、忌口和用餐人数，整理需求、优化餐品组合，并在可用数据范围内核对菜单与优惠。

> **核心目标：少问问题，给出清晰推荐；记住明确偏好，涉及关键操作时先确认。**

## 核心能力

- **自然语言点餐**：从日常表达中提取预算、人数、口味及忌口，优先给出一个明确首选。
- **个性化记忆**：通过本地记忆模块保存用户明确表达的偏好，并支持查看和清除。
- **配餐优化**：根据预算等约束组合餐品，支持多人方案与费用分摊计算。
- **MCP 接口封装**：为门店、菜单、活动、优惠及价格核验提供接口适配。
- **操作安全**：查询和计算可按需求执行；领券、下单、取消等有副作用的操作需要明确授权。

## 快速开始

### WorkBuddy 用户（推荐）

无需克隆源码或运行命令，下载 Skill 后导入 WorkBuddy 即可使用。

**[下载麦麦搭子 Skill 安装包（ZIP）](https://github.com/jinke666/-McMeal-Mat/raw/refs/heads/main/dist/mcmeal-mate-skill.zip)**

也可以直接获取 [SKILL.md](https://raw.githubusercontent.com/jinke666/-McMeal-Mat/main/SKILL.md)。

导入并启用后，可以尝试：

> 帮我选一份 30 元以内、不辣的鸡肉午餐。

如需查询实时门店、菜单、优惠或价格，还需要在 WorkBuddy 中单独配置可用的麦当劳 MCP 连接器。

### 开发者本地运行

需要调试本地算法、记忆模块或 MCP 客户端时，再运行源码：

```bash
git clone https://github.com/jinke666/-McMeal-Mat.git mcmeal-mate
cd mcmeal-mate
python -m pip install -e .
python scripts/demo.py
```

开发与接口配置说明见 [MCP 集成指南](MCP_INTEGRATION.md)。

## 项目结构

| 路径 | 说明 |
| --- | --- |
| `SKILL.md` | Skill 行为规则与交互流程 |
| `mcmeal/` | 本地配餐优化、记忆与相关逻辑 |
| `tests/` | 自动化测试 |
| `scripts/` | 本地演示与辅助脚本 |
| `MCP_INTEGRATION.md` | MCP 配置与集成说明 |

## 能力边界

- 实时菜单、优惠和价格依赖已配置的 MCP 服务及其实际响应。
- 未连接或调用失败时，演示数据与估算结果不能视为实时报价。
- 本仓库不代表已打通完整的官方下单与支付闭环。
- 麦当劳相关商标及服务归其各自权利人所有。本项目为独立开发项目。

---

**McMeal-Mate** · AI 点餐助手
