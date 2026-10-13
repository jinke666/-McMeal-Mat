"""
McMeal-Mate 命令行交互工具 (CLI)
提供高颜值彩色终端输出、运筹优化试算与麦当劳点餐决策
"""

import sys
import argparse

# 确保在 Windows 控制台支持 UTF-8 打印
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from mcmeal.agent import McMealAgent
from mcmeal.mcp_client import McDonaldMCPClient, DEFAULT_MENU_ITEMS
from mcmeal.models import MemberPreference, GroupOrderPlan, DataReliability

# ANSI 颜色格式化
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

BANNER = f"""
{YELLOW}{BOLD}==================================================================
  🍔  McMeal-Mate (麦麦搭子) —— 低摩擦智能点餐与双人协同  🍔
        少问一句、少绕一步；推荐靠谱，关键操作有确认
=================================================================={RESET}
"""

def print_plan(idx: int, plan):
    """格式化打印推荐配餐方案"""
    print(f"\n{CYAN}{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f" {BOLD}{plan.plan_name}{RESET}")
    print(f" 💡 {plan.explanation}")
    print(f"{CYAN}─────────────────────────────────────────────────────────────{RESET}")
    
    print(f"  {BOLD}餐品清单：{RESET}")
    for item in plan.items:
        print(f"    • {item.name:<16} 单价: ¥{item.original_price:>4.1f}  |  热量: {item.nutrition.energy_kcal:>4.0f} kcal  |  蛋白质: {item.nutrition.protein:>3.0f}g")
    
    if plan.applied_coupons:
        print(f"  {BOLD}已应用优惠：{RESET}")
        for cp in plan.applied_coupons:
            print(f"    🏷️  {cp.title} (优惠立减 ¥{cp.discount_amount:.1f})")

    print(f"{CYAN}─────────────────────────────────────────────────────────────{RESET}")
    print(f"  💰 {BOLD}原价合计:{RESET} ¥{plan.original_total:.1f}   "
          f"➡️  {GREEN}{BOLD}实付优惠价:{RESET} ¥{plan.actual_total:.1f}   "
          f"🎉 {YELLOW}{BOLD}立省:{RESET} ¥{plan.saved_amount:.1f} ({plan.discount_rate*10:.1f}折)  "
          f"[{CYAN}{plan.reliability.value}{RESET}]")
    print(f"  🥗 {BOLD}营养指标:{RESET} 总热量: {plan.total_nutrition.energy_kcal:.0f} kcal | 蛋白质: {plan.total_nutrition.protein:.0f}g | 脂肪: {plan.total_nutrition.fat:.0f}g | 钠: {plan.total_nutrition.sodium:.0f}mg")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

def print_group_plan(idx: int, plan: GroupOrderPlan):
    """格式化打印多人/双人协同方案及公平分摊账单"""
    print(f"\n{CYAN}{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f" {BOLD}{plan.plan_name}{RESET}  [{GREEN}{plan.reliability.value}{RESET}]")
    print(f" 💡 {plan.explanation}")
    print(f"{CYAN}─────────────────────────────────────────────────────────────{RESET}")

    if plan.shared_items:
        print(f"  {BOLD}🍿 团队共享餐品：{RESET}")
        for s_item in plan.shared_items:
            tag_str = f" [{YELLOW}{','.join(s_item.tags)}{RESET}]" if s_item.tags else ""
            print(f"    • {s_item.name:<16}{tag_str} 单价: ¥{s_item.original_price:>4.1f}")

    print(f"\n  {BOLD}👥 个人餐品与精准分摊账单（公平数学模型）：{RESET}")
    for m in plan.members:
        print(f"   ┌─ 👤 {BOLD}{m.member_name}{RESET}:")
        for item in m.individual_items:
            tag_str = f" [{YELLOW}{','.join(item.tags)}{RESET}]" if item.tags else ""
            print(f"   │  • {item.name:<16}{tag_str} 单价: ¥{item.original_price:>4.1f}")
        print(f"   │  💰 个人原价: ¥{m.individual_original_total:.1f} + 共享分摊: ¥{m.shared_items_cost_share:.1f} - 优惠分摊: ¥{m.applied_discount_share:.1f}")
        print(f"   │  ➡️  {GREEN}{BOLD}最终应付转账: ¥{m.final_payable:.1f}{RESET}  (立省: ¥{m.saved_amount:.1f})")
        print(f"   └─ 🥗 个人摄入: {m.nutrition.energy_kcal:.0f} kcal | 蛋白质: {m.nutrition.protein:.0f}g")

    print(f"{CYAN}─────────────────────────────────────────────────────────────{RESET}")
    print(f"  💰 {BOLD}整单原价:{RESET} ¥{plan.total_original:.1f}   "
          f"➡️  {GREEN}{BOLD}整单实付:{RESET} ¥{plan.total_actual:.1f}   "
          f"👥 {BOLD}人均实付:{RESET} ¥{plan.per_person_avg:.1f}   "
          f"🎉 {YELLOW}{BOLD}全员立省:{RESET} ¥{plan.total_saved:.1f}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

def run_cli():
    parser = argparse.ArgumentParser(description="McMeal-Mate: 麦麦搭子 —— 双人协同点餐与公平分摊智能体")
    parser.add_argument("-b", "--budget", type=float, default=25.0, help="预算上限 (元)")
    parser.add_argument("-p", "--prompt", type=str, default="", help="自然语言需求描述")
    parser.add_argument("--city", type=str, default="上海", help="点餐城市")
    parser.add_argument("--user-id", type=str, default="default_user", help="用户标识")
    parser.add_argument("--pool", action="store_true", help="演示麦乐送 39 元免配拼单凑单算法")
    parser.add_argument("--duo", action="store_true", help="演示双人协同点餐与公平分摊 (支持不同忌口/预算)")
    parser.add_argument("--view-memory", action="store_true", help="查看麦麦当前记录的长期偏好与记忆 (透明度保障)")
    parser.add_argument("--clear-memory", action="store_true", help="一键清除麦麦记录的该用户全部偏好 (隐私遗忘权)")
    parser.add_argument("--interactive", action="store_true", help="启动交互式对话模式")

    args = parser.parse_args()
    print(BANNER)

    agent = McMealAgent()

    if args.clear_memory:
        agent.erase_user_preferences(args.user_id)
        print(f"{GREEN}🧹 已成功清除用户 [{args.user_id}] 的所有偏好与历史记忆！{RESET}")
        return

    if args.view_memory:
        summary = agent.get_user_memory_summary(args.user_id)
        if summary:
            print(f"{CYAN}{BOLD}🧠 麦麦记录的长期偏好与画像 (用户: {args.user_id})：{RESET}")
            print(summary)
        else:
            print(f"{YELLOW}目前没有存储用户 [{args.user_id}] 的任何偏好记录。{RESET}")
        return

    if args.duo:
        print(f"{YELLOW}>>> 演示模式：双人协同点餐与公平分摊 (符合 v1.0 规格书 2.2 节) <<<{RESET}")
        members = [
            MemberPreference(name="小明(喜肉/可吃辣)", budget=35.0, is_spicy_ok=True),
            MemberPreference(name="小红(不吃辣/要冷饮)", budget=30.0, is_spicy_ok=False, excluded_items=["麦辣鸡腿汉堡", "麦辣鸡翅-2块"])
        ]
        result = agent.process_group_order(members, city=args.city)
        print(f"{CYAN}🤖 麦麦店员:{RESET} {result.get('maimai_speech')}")
        store = result.get("store")
        if store:
            print(f"{GREEN}📍 匹配餐厅:{RESET} {store.store_name} ({store.address})")
        for idx, plan in enumerate(result.get("plans", []), 1):
            print_group_plan(idx, plan)
        return

    if args.pool:
        print(f"{YELLOW}>>> 演示模式：麦乐送 39 元免外送费起送门槛凑单算法 <<<{RESET}")
        sample_cart = [DEFAULT_MENU_ITEMS[0]] # 双层吉士汉堡 23.5元
        res = agent.solve_delivery_pooling(sample_cart, min_spend=39.0)
        print(f"当前购物车总计: ¥{res['current_total']:.1f}")
        print(f"目标免配门槛:   ¥{res['target_spend']:.1f}")
        print(f"运筹推荐补位餐品: {[i.name for i in res['recommended_additions']]}")
        print(f"最优凑单结果:   {res['explanation']}")
        return

    query = args.prompt or f"预算 {args.budget} 元，想吃汉堡和可乐，帮我配最省钱的吃法"
    print(f"{BLUE}🔍 输入需求:{RESET} {query}")
    print(f"{BLUE}⚙️  正在调用麦当劳 MCP 服务 (获取时间、日历、自动领券、查询门店与餐品)...{RESET}")

    result = agent.process_request(query, city=args.city, user_id=args.user_id)
    store = result.get("store")
    if store:
        print(f"{GREEN}📍 匹配餐厅:{RESET} {store.store_name} ({store.address}) - 距离: {store.distance}m")

    print(f"{GREEN}🎫 优惠资产:{RESET} {result.get('coupon_status')}")
    if result.get("memory_summary"):
        print(f"{CYAN}🧠 记忆匹配:{RESET}\n{result.get('memory_summary')}")
    
    plans = result.get("plans", [])
    if not plans:
        print(f"{RED}未找到符合全部严苛约束的配餐，建议适当提高预算或放宽忌口。{RESET}")
        return

    print(f"\n{YELLOW}{BOLD}🏆 麦门运筹学算法已为您完成多目标寻优，推荐 Top 候选方案：{RESET}")
    for idx, plan in enumerate(plans, 1):
        print_plan(idx, plan)

if __name__ == "__main__":
    run_cli()
