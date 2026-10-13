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

        # 4. 真实算价校验
        verified_plans = []
        for plan in optimal_plans:
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
            plan.reliability = calc_res.get("reliability", DataReliability.LIVE_VERIFIED)
            verified_plans.append(plan)

        return {
            "query": user_prompt,
            "maimai_speech": "我按你的条件先筛了一轮，下面给你一个优先推荐；价格与优惠状态以本次核验结果为准。",
            "memory_summary": self.memory.get_context_for_prompt(user_id),
            "constraint": constraint,
            "store": selected_store,
            "calendar": calendar_info,
            "coupon_status": "已检查优惠信息；未自动领取任何优惠券"
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

        return {
            "members_count": len(members),
            "members": [m.name for m in members],
            "maimai_speech": f"我按 {len(members)} 人各自的偏好筛好了方案，也把共享餐品和分摊金额列清楚了。",
            "store": selected_store,
            "coupon_status": "已查询当前可用优惠；未自动领取任何优惠券",
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

        # 忌口处理
        if "不吃辣" in text:
            constraint.excluded_items.extend(["麦辣鸡腿汉堡", "麦辣鸡翅-2块"])
        if "不要可乐" in text:
            constraint.excluded_items.append("可乐中杯")
        if "去冰" in text or "热饮" in text:
            constraint.excluded_items.extend(["冰美式中杯"])

        return constraint

    def _apply_memory_preferences(self, user_id: str, constraint: OptimizationConstraint, text: str) -> None:
        """从长期记忆中载入偏好，并把本次对话中明确表达的偏好持久化更新"""
        # 1. 用户本次主动表达偏好 -> 持久化为 user-stated
        if "不吃辣" in text:
            self.memory.set_preference(user_id, "spicy_ok", "false", source="user-stated")
        elif "可以吃辣" in text or "能吃辣" in text:
            self.memory.set_preference(user_id, "spicy_ok", "true", source="user-stated")

        if "不要可乐" in text:
            self.memory.set_preference(user_id, "avoid_coke", "true", source="user-stated")

        # 2. 从长期记忆中提取并填充未在当前 prompt 中指定的约束
        prefs = {p.key: p.value for p in self.memory.list_preferences(user_id)}

        # 若记忆中记录了不吃辣，且当前 prompt 没有显式要求辣味
        if prefs.get("spicy_ok") == "false" and "能吃辣" not in text and "可以吃辣" not in text:
            for item in ["麦辣鸡腿汉堡", "麦辣鸡翅-2块"]:
                if item not in constraint.excluded_items:
                    constraint.excluded_items.append(item)

        if prefs.get("avoid_coke") == "true" and "可乐" not in text:
            if "可乐中杯" not in constraint.excluded_items:
                constraint.excluded_items.append("可乐中杯")

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

