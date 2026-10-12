"""
McMeal-Mate 完整功能演示脚本
演示 3 个真实生活场景：
1. 20元极限吃饱省钱模式
2. 程序员加班减脂控卡高蛋白模式
3. 办公室麦乐送 39 元凑单免配送费模式
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 模块搜索路径
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcmeal.agent import McMealAgent
from mcmeal.cli import print_plan, BANNER, YELLOW, GREEN, BLUE, RESET
from mcmeal.mcp_client import DEFAULT_MENU_ITEMS

def run_scenarios():
    print(BANNER)
    agent = McMealAgent()

    print(f"\n{YELLOW}================== 场景 1：20 元极限吃饱省钱模式 =================={RESET}")
    res1 = agent.process_request("预算 20 元，想要汉堡和饮料，帮我找出最划算的吃法")
    for idx, plan in enumerate(res1.get("plans", []), 1):
        print_plan(idx, plan)

    print(f"\n{YELLOW}================== 场景 2：程序员加班减脂控卡模式 =================={RESET}")
    res2 = agent.process_request("热量不要超过 700 大卡，至少 30g 蛋白质，预算 35 元，不要可乐")
    for idx, plan in enumerate(res2.get("plans", []), 1):
        print_plan(idx, plan)

    print(f"\n{YELLOW}================== 场景 3：办公室麦乐送 39 元免配凑单 =================={RESET}")
    cart = [item for item in DEFAULT_MENU_ITEMS if item.name == "巨无霸"]
    res3 = agent.solve_delivery_pooling(cart, min_spend=39.0)
    print(f"当前购物车: 【巨无霸】(¥{cart[0].price})")
    print(f"目标免配起送金额: ¥{res3['target_spend']}")
    print(f"算法推荐凑单方案: {[i.name for i in res3['recommended_additions']]}")
    print(f"凑单分析: {res3['explanation']}")

    print(f"\n{YELLOW}================== 场景 4：双人协同点餐与公平分摊 (核心差异化) =================={RESET}")
    from mcmeal.models import MemberPreference
    from mcmeal.cli import print_group_plan
    members = [
        MemberPreference(name="小明(爱吃肉/吃辣)", budget=35.0, is_spicy_ok=True),
        MemberPreference(name="小红(不吃辣/要冷饮)", budget=30.0, is_spicy_ok=False, excluded_items=["麦辣鸡腿汉堡", "麦辣鸡翅-2块"])
    ]
    res4 = agent.process_group_order(members)
    print(f"🤖 麦麦店员: {res4.get('maimai_speech')}")
    for idx, plan in enumerate(res4.get("plans", []), 1):
        print_group_plan(idx, plan)

    print(f"\n{GREEN}全部场景演示完成！麦麦搭子 McMeal-Mate 运行正常。{RESET}\n")

if __name__ == "__main__":
    run_scenarios()
