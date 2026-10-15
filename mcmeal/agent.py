"""
智能配餐与省钱协调智能体 (McMealAgent)
协调麦当劳 MCP 服务、用户意图解析、运筹学优化器及真实算价验证
"""

import re
from typing import Dict, Any, List, Optional
from mcmeal.mcp_client import McDonaldMCPClient
from mcmeal.optimizer import McOptimizer
from mcmeal.memory import McMealMemory, UserPreference
from mcmeal.models import (
    OptimizationConstraint, OptimizedPlan, FoodCategory,
    MenuItem, Coupon, StoreInfo, DataReliability,
    MemberPreference, GroupOrderPlan
)

class McMealAgent:
    """麦膳精算师智能体"""

    def __init__(self, mcp_client: Optional[McDonaldMCPClient] = None, memory: Optional[McMealMemory] = None):
        self.client = mcp_client or McDonaldMCPClient()
        self.memory = memory or McMealMemory()

    def process_request(self, user_prompt: str, city: str = "上海", keyword: str = "人民广场", user_id: str = "default_user") -> Dict[str, Any]:
        """
        处理用户的点餐/省钱/配餐请求全流程：
        1. 意图解析 (提取预算、偏好、卡路里、忌口等) 并结合长期记忆
        2. MCP 服务资产同步 (一键领券、拉取门店与在售餐品、同步营养库)
        3. 运筹优化求解 (多约束背包算法)
        4. 真实算价校验与结果装配
        """
        constraint = self._parse_intent(user_prompt)
        self._apply_memory_preferences(user_id, constraint, user_prompt)

        # 1. 只读同步：查询可用优惠和活动；普通推荐不得擅自改变账户状态或自动领券
        available_coupons = self.client.get_available_coupons()
        calendar_info = self.client.get_campaign_calendar()

        # 2. 门店与餐品拉取
        stores = self.client.query_nearby_stores(city=city, keyword=keyword)
        selected_store = stores[0] if stores else None
        if not selected_store:
            return {
                "query": user_prompt,
                "maimai_speech": "我暂时没查到这个区域可用的门店，所以不能可靠核对菜单和价格。告诉我城市/商圈或选一家常用门店，我就接着找；其他条件不用重说。",
                "memory_summary": self.memory.get_context_for_prompt(user_id),
                "constraint": constraint,
                "store": None,
                "calendar": calendar_info,
                "coupon_status": "已检查优惠信息；未自动领取任何优惠券",
                "plans": [],
            }
        store_code = selected_store.store_code

        menu = self.client.get_store_meals(store_code=store_code)

        # 3. 运行运筹优化求解器
        optimizer = McOptimizer(menu=menu, coupons=available_coupons)
        optimal_plans = optimizer.solve(constraint)

        # 4. 真实算价校验与客制化制作备注处理
        verified_plans = []
        for plan in optimal_plans:
            # 附加餐品客制化制作备注 (如饮料去冰、汉堡去酸黄瓜)
            for item in plan.items:
                if item.category == FoodCategory.DRINK:
                    for note in constraint.custom_notes:
                        if note in ["去冰", "少冰", "多冰", "常温", "热饮"] and note not in item.customizations:
                            item.customizations.append(note)
                elif item.category == FoodCategory.MAIN:
                    for note in constraint.custom_notes:
                        if note in ["去酸黄瓜", "去洋葱", "去酱", "去芝士"] and note not in item.customizations:
                            item.customizations.append(note)
                elif item.category == FoodCategory.SNACK:
                    for note in constraint.custom_notes:
                        if note in ["加番茄酱", "加甜酸酱"] and note not in item.customizations:
                            item.customizations.append(note)

            plan.dietary_notes = [f"{i.name}({','.join(i.customizations)})" for i in plan.items if i.customizations]

            # 忌口/辣味/过敏原主动提醒
            spicy_items = [i.name for i in plan.items if "辣" in i.name or "辣" in "".join(i.tags)]
            if spicy_items:
                plan.dietary_alerts.append(f"含辣餐品: {'、'.join(spicy_items)}")

            deduction = round(sum(i.price for i in plan.items) - plan.actual_total, 2)
            calc_res = self.client.calculate_price(
                plan.items,
                coupon_ids=[c.coupon_id for c in plan.applied_coupons],
                discount_deduction=max(0.0, deduction),
                store_code=store_code,
            )
            plan.actual_total = calc_res.get("payable_amount", plan.actual_total)
            plan.original_total = calc_res.get("original_amount", plan.original_total)
            plan.saved_amount = round(plan.original_total - plan.actual_total, 2)
            plan.discount_rate = round(plan.actual_total / plan.original_total, 2) if plan.original_total > 0 else 1.0
            plan.reliability = calc_res.get("reliability", DataReliability.ESTIMATED)
            verified_plans.append(plan)

        # 构造贴心、低摩擦的麦麦语音提示 (伴随式忌口与制作备注轻问询)
        primary_plan = verified_plans[0] if verified_plans else None
        if primary_plan and primary_plan.dietary_notes:
            notes_str = "、".join(primary_plan.dietary_notes)
            maimai_speech = f"我按你的条件筛出了优先推荐，已为你标注客制化备注【{notes_str}】。如果有其他忌口或想换不辣的，随时告诉我～"
        elif primary_plan and primary_plan.dietary_alerts:
            alerts_str = "、".join(primary_plan.dietary_alerts)
            maimai_speech = f"我按你的条件筛出了优先推荐。💡 方案包含【{alerts_str}】，饮品默认为常规冰饮。如果有忌口（如不吃辣/过敏原）或需要去冰/去酸黄瓜备注，随时告诉我～"
        else:
            maimai_speech = "我按你的条件筛出了优先推荐。💡 餐品默认为常规标准制作；若有去冰、去酸黄瓜或特殊忌口备注，随时告诉我～"

        return {
            "query": user_prompt,
            "maimai_speech": maimai_speech,
            "memory_summary": self.memory.get_context_for_prompt(user_id),
            "constraint": constraint,
            "store": selected_store,
            "calendar": calendar_info,
            "coupon_status": "已检查优惠信息；未自动领取任何优惠券",
            "plans": verified_plans
        }

    def process_group_order(self, members: List[MemberPreference], city: str = "上海", keyword: str = "人民广场") -> Dict[str, Any]:
        """
        处理双人/多人协同点餐全流程 (符合 v1.0 规格书 2.2 节核心差异化)：
        1. 独立解析每位参与者偏好、忌口、预算
        2. 选定最佳共享餐品
        3. 求解协同组合方案并按数学公平比例分摊
        4. 真实算价校验与结果装配
        """
        # 1. 只读查询可用优惠；多人点餐推荐同样不得默认修改账户状态
        available_coupons = self.client.get_available_coupons()

        # 2. 门店与在售餐品
        stores = self.client.query_nearby_stores(city=city, keyword=keyword)
        selected_store = stores[0] if stores else None
        if not selected_store:
            return {
                "members_count": len(members),
                "members": [m.name for m in members],
                "maimai_speech": "我暂时没查到这个区域可用的门店，不能可靠比较实时菜单。告诉我城市/商圈或选一家常用门店，我就接着算。",
                "store": None,
                "coupon_status": "已检查优惠信息；未自动领取任何优惠券",
                "plans": [],
            }
        store_code = selected_store.store_code
        menu = self.client.get_store_meals(store_code=store_code)

        # 3. 运筹求解双人方案
        optimizer = McOptimizer(menu=menu, coupons=available_coupons)
        group_plans = optimizer.solve_group_order(members)
        # 多人方案目前由本地优化器计算，尚未逐单调用官方 calculate-price 复核，不能标记 LIVE_VERIFIED。
        group_reliability = (
            DataReliability.ESTIMATED
            if getattr(self.client, "token", None)
            and getattr(self.client, "last_menu_reliability", DataReliability.MOCK) == DataReliability.LIVE_VERIFIED
            else DataReliability.MOCK
        )
        for plan in group_plans:
            plan.reliability = group_reliability
            group_notes = []
            group_alerts = []
            for m_share, m_pref in zip(plan.members, members):
                member_notes_list = []
                customs = list(getattr(m_pref, "customizations", []) or [])
                if getattr(m_pref, "notes", None) and m_pref.notes not in customs:
                    customs.append(m_pref.notes)
                for item in m_share.individual_items:
                    for c in customs:
                        if c in ["去冰", "少冰", "热饮", "常温"] and item.category == FoodCategory.DRINK:
                            if c not in item.customizations:
                                item.customizations.append(c)
                        elif c in ["去酸黄瓜", "去洋葱", "去酱", "去芝士"] and item.category == FoodCategory.MAIN:
                            if c not in item.customizations:
                                item.customizations.append(c)
                    if item.customizations:
                        member_notes_list.append(f"{item.name}({','.join(item.customizations)})")
                    if "辣" in item.name or "辣" in "".join(item.tags):
                        group_alerts.append(f"{m_pref.name}包含辣味({item.name})")

                m_share.member_notes = member_notes_list
                if member_notes_list:
                    group_notes.append(f"{m_pref.name}: {', '.join(member_notes_list)}")

            plan.dietary_notes = group_notes
            plan.dietary_alerts = group_alerts

        maimai_speech = (
            f"我按 {len(members)} 位伙伴各自的偏好筛好了方案，包含独立餐品、共享小食和分摊明细。"
            f"💡 若有伙伴需要调整去冰、去酸黄瓜等制作备注或特殊忌口，随时告诉我～"
        )

        return {
            "members_count": len(members),
            "members": [m.name for m in members],
            "maimai_speech": maimai_speech,
            "store": selected_store,
            "coupon_status": "已检查优惠信息；未自动领取任何优惠券",
            "plans": group_plans
        }

    def solve_delivery_pooling(self, current_items: List[MenuItem], min_spend: float = 39.0) -> Dict[str, Any]:
        """凑单免配送费辅助计算"""
        menu = self.client.get_store_meals(store_code="1450713")
        optimizer = McOptimizer(menu=menu)
        additions, waste, exp = optimizer.optimize_delivery_pooling(current_items, min_spend)
        return {
            "current_total": sum(i.price for i in current_items),
            "target_spend": min_spend,
            "recommended_additions": additions,
            "overflow_amount": waste,
            "explanation": exp
        }

    def _parse_intent(self, text: str) -> OptimizationConstraint:
        """规则+启发式意图解析器"""
        constraint = OptimizationConstraint()

        # 预算提取 (如 "25元", "预算30", "不超过50块")
        budget_match = re.search(r'(?:预算|不超过|在)?\s*(\d+(?:\.\d+)?)\s*(?:元|块|RMB|rmb)?', text)
        if budget_match:
            val = float(budget_match.group(1))
            if 10 <= val <= 300:
                constraint.max_budget = val
            elif val > 0 and val < 10:
                # 可能是件数或误判，若明确带"元"则采纳
                if "元" in text or "块" in text:
                    constraint.max_budget = val

        # 默认适中预算
        if constraint.max_budget > 900:
            constraint.max_budget = 30.0

        # 卡路里/热量提取 (如 "低于600大卡", "500卡", "低卡")
        cal_match = re.search(r'(\d+)\s*(?:大卡|卡|kcal|Kcal)', text)
        if cal_match:
            constraint.max_calories = float(cal_match.group(1))
        elif "低卡" in text or "减脂" in text or "减肥" in text:
            constraint.max_calories = 650.0

        # 高蛋白需求
        if "增肌" in text or "高蛋白" in text:
            constraint.min_protein = 30.0

        # 必点与喜好
        if "汉堡" in text or "牛堡" in text or "鸡腿堡" in text:
            constraint.required_categories.append(FoodCategory.MAIN)
        if "可乐" in text or "咖啡" in text or "饮料" in text or "饮品" in text:
            constraint.required_categories.append(FoodCategory.DRINK)
        if "薯条" in text or "麦乐鸡" in text or "鸡翅" in text or "小食" in text:
            constraint.required_categories.append(FoodCategory.SNACK)

        # 忌口处理 (扩展辣、海鲜、牛肉、奶制品等)
        if any(w in text for w in ["不吃辣", "忌辣", "不要辣", "不能吃辣", "微辣也不行"]):
            constraint.is_spicy_ok = False
            constraint.excluded_items.extend(["麦辣鸡腿汉堡", "麦辣鸡翅-2块", "龙焰鸡腿堡"])
        if any(w in text for w in ["海鲜过敏", "不吃海鲜", "不吃鱼"]):
            constraint.excluded_items.extend(["麦香鱼", "双层深海鳕鱼堡", "三文鱼双虾至尊月堡"])
        if any(w in text for w in ["不吃牛肉", "不吃牛"]):
            constraint.excluded_items.extend(["双层吉士汉堡", "巨无霸", "培根安格斯厚牛堡", "培根蔬萃双层牛堡"])
        if any(w in text for w in ["乳糖不耐", "不喝牛奶", "牛奶过敏", "对牛奶"]):
            constraint.excluded_items.extend(["纯牛奶（盒装）", "奥利奥麦旋风", "圆筒冰淇淋", "新地"])
        if "不要可乐" in text:
            constraint.excluded_items.append("可乐中杯")
        if "热饮" in text and "去冰" not in text:
            constraint.excluded_items.extend(["冰美式中杯"])

        # 客制化制作备注解析 (饮品去冰/少冰、汉堡去酸黄瓜/去洋葱/去酱等)
        if "去冰" in text or "不加冰" in text:
            constraint.custom_notes.append("去冰")
        elif "少冰" in text:
            constraint.custom_notes.append("少冰")
        elif "多冰" in text:
            constraint.custom_notes.append("多冰")
        elif "常温" in text:
            constraint.custom_notes.append("常温")
        elif "热饮" in text:
            constraint.custom_notes.append("热饮")

        if "去酸黄瓜" in text or "不要酸黄瓜" in text or "不加酸黄瓜" in text:
            constraint.custom_notes.append("去酸黄瓜")
        if "去洋葱" in text or "不要洋葱" in text:
            constraint.custom_notes.append("去洋葱")
        if "去酱" in text or "不要酱" in text or "少酱" in text:
            constraint.custom_notes.append("去酱")
        if "多放番茄酱" in text or "加番茄酱" in text:
            constraint.custom_notes.append("加番茄酱")
        if "去芝士" in text or "不要芝士" in text:
            constraint.custom_notes.append("去芝士")

        return constraint

    def _apply_memory_preferences(self, user_id: str, constraint: OptimizationConstraint, text: str) -> None:
        """从长期记忆中载入偏好，并把本次对话中明确表达的偏好持久化更新"""
        # 1. 用户本次主动表达偏好与备注 -> 持久化为 user-stated
        if "不吃辣" in text:
            self.memory.set_preference(user_id, "spicy_ok", "false", source="user-stated")
        elif "可以吃辣" in text or "能吃辣" in text:
            self.memory.set_preference(user_id, "spicy_ok", "true", source="user-stated")

        if "不要可乐" in text:
            self.memory.set_preference(user_id, "avoid_coke", "true", source="user-stated")

        if "去冰" in text:
            self.memory.set_preference(user_id, "drink_ice_note", "去冰", source="user-stated")
        if "去酸黄瓜" in text:
            self.memory.set_preference(user_id, "pickle_note", "去酸黄瓜", source="user-stated")

        # 2. 从长期记忆中提取并填充未在当前 prompt 中指定的约束与制作备注
        prefs = {p.key: p.value for p in self.memory.list_preferences(user_id)}

        # 若记忆中记录了不吃辣，且当前 prompt 没有显式要求辣味
        if prefs.get("spicy_ok") == "false" and "能吃辣" not in text and "可以吃辣" not in text:
            for item in ["麦辣鸡腿汉堡", "麦辣鸡翅-2块", "龙焰鸡腿堡"]:
                if item not in constraint.excluded_items:
                    constraint.excluded_items.append(item)

        if prefs.get("avoid_coke") == "true" and "可乐" not in text:
            if "可乐中杯" not in constraint.excluded_items:
                constraint.excluded_items.append("可乐中杯")

        # 载入长期饮品/餐品制作偏好
        if "drink_ice_note" in prefs and not any(n in constraint.custom_notes for n in ["去冰", "少冰", "多冰", "常温", "热饮"]):
            constraint.custom_notes.append(prefs["drink_ice_note"])
        if "pickle_note" in prefs and "去酸黄瓜" not in constraint.custom_notes:
            constraint.custom_notes.append(prefs["pickle_note"])

        if "calorie_target" in prefs and constraint.max_calories >= 900.0:
            try:
                constraint.max_calories = float(prefs["calorie_target"])
            except ValueError:
                pass

    def set_user_preference(self, user_id: str, key: str, value: str, source: str = "user-stated") -> None:
        """设置用户偏好"""
        self.memory.set_preference(user_id, key, value, source)

    def erase_user_preferences(self, user_id: str, key: Optional[str] = None) -> int:
        """擦除用户偏好"""
        return self.memory.erase_preferences(user_id, key)

    def get_user_memory_summary(self, user_id: str) -> str:
        """获取用户记忆摘要"""
        return self.memory.get_context_for_prompt(user_id)

    def format_plan_markdown(self, plan: OptimizedPlan) -> str:
        """生成带餐品官方图片、价格与客制化备注的 Markdown 表格卡片"""
        lines = [
            f"### 🍔 方案推荐：{plan.plan_name} [{plan.reliability.value}]",
            f"💡 *{plan.explanation}*",
            "",
            "| 餐品名称 | 官方图片 | 单品原价 | 客制化备注 | 热量 |",
            "| :--- | :---: | :---: | :--- | :---: |"
        ]
        for item in plan.items:
            img_tag = f'<img src="{item.image_url}" width="64" height="64" alt="{item.name}" />' if item.image_url else "🍔"
            notes = "、".join(item.customizations) if item.customizations else "常规制作"
            lines.append(f"| **{item.name}** | {img_tag} | ¥{item.original_price:.1f} | {notes} | {item.nutrition.energy_kcal:.0f} kcal |")

        lines.append("")
        lines.append(f"- 💰 **价格结算**：原价 ¥{plan.original_total:.1f} ➡️ **实付 ¥{plan.actual_total:.1f}** (立省 ¥{plan.saved_amount:.1f})")
        if plan.dietary_notes:
            lines.append(f"- 📝 **定制备注**：{'；'.join(plan.dietary_notes)}")
        if plan.dietary_alerts:
            lines.append(f"- ⚠️ **忌口提醒**：{'；'.join(plan.dietary_alerts)}")
        return "\n".join(lines)

    def format_group_plan_markdown(self, plan: GroupOrderPlan) -> str:
        """生成多人双人带图片与分摊明细的 Markdown 账单"""
        lines = [
            f"### 👫 协同推荐：{plan.plan_name} [{plan.reliability.value}]",
            f"💡 *{plan.explanation}*",
            "",
            "#### 🍿 团队共享餐品：",
            "| 共享餐品 | 图片 | 单价 |",
            "| :--- | :---: | :---: |"
        ]
        for s in plan.shared_items:
            img = f'<img src="{s.image_url}" width="60" height="60" alt="{s.name}" />' if s.image_url else "🍿"
            lines.append(f"| **{s.name}** | {img} | ¥{s.original_price:.1f} |")

        lines.append("")
        lines.append("#### 👥 个人专属餐品与精准分摊：")
        for m in plan.members:
            lines.append(f"- **👤 {m.member_name}**：")
            for item in m.individual_items:
                note_str = f" [{','.join(item.customizations)}]" if item.customizations else ""
                lines.append(f"  • {item.name}{note_str} (¥{item.original_price:.1f})")
            lines.append(f"  ➡️ **应付转账：¥{m.final_payable:.1f}** (原价: ¥{m.individual_original_total:.1f} + 共享: ¥{m.shared_items_cost_share:.1f} - 优惠: ¥{m.applied_discount_share:.1f})")

        lines.append("")
        lines.append(f"💰 **整单结算**：原价 ¥{plan.total_original:.1f} ➡️ **整单实付 ¥{plan.total_actual:.1f}**（全员立省 ¥{plan.total_saved:.1f}）")
        if plan.dietary_notes:
            lines.append(f"📝 **全单备注**：{'；'.join(plan.dietary_notes)}")
        if plan.dietary_alerts:
            lines.append(f"⚠️ **忌口提醒**：{'；'.join(plan.dietary_alerts)}")
        return "\n".join(lines)

