"""
智能配餐与省钱协调智能体 (McMealAgent)
协调麦当劳 MCP 服务、用户意图解析、运筹学优化器及真实算价验证
"""

import re
from typing import Dict, Any, List, Optional
from mcmeal.mcp_client import McDonaldMCPClient
from mcmeal.optimizer import McOptimizer
from mcmeal.models import (
    OptimizationConstraint, OptimizedPlan, FoodCategory,
    MenuItem, Coupon, StoreInfo
)

class McMealAgent:
    """麦膳精算师智能体"""

    def __init__(self, mcp_client: Optional[McDonaldMCPClient] = None):
        self.client = mcp_client or McDonaldMCPClient()

    def process_request(self, user_prompt: str, city: str = "上海", keyword: str = "人民广场") -> Dict[str, Any]:
        """
        处理用户的点餐/省钱/配餐请求全流程：
        1. 意图解析 (提取预算、偏好、卡路里、忌口等)
        2. MCP 服务资产同步 (一键领券、拉取门店与在售餐品、同步营养库)
        3. 运筹优化求解 (多约束背包算法)
        4. 真实算价校验与结果装配
        """
        constraint = self._parse_intent(user_prompt)

        # 1. 资产与日历协同 (自动领券与活动扫描)
        coupon_claim_result = self.client.auto_bind_coupons()
        available_coupons = self.client.get_available_coupons()
        calendar_info = self.client.get_campaign_calendar()

        # 2. 门店与餐品拉取
        stores = self.client.query_nearby_stores(city=city, keyword=keyword)
        selected_store = stores[0] if stores else None
        store_code = selected_store.store_code if selected_store else "1450713"

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
                discount_deduction=max(0.0, deduction)
            )
            plan.actual_total = calc_res.get("payable_amount", plan.actual_total)
            plan.original_total = calc_res.get("original_amount", plan.original_total)
            plan.saved_amount = round(plan.original_total - plan.actual_total, 2)
            plan.discount_rate = round(plan.actual_total / plan.original_total, 2) if plan.original_total > 0 else 1.0
            verified_plans.append(plan)

        return {
            "query": user_prompt,
            "constraint": constraint,
            "store": selected_store,
            "calendar": calendar_info,
            "coupon_status": coupon_claim_result.get("message", "已同步优惠券资产"),
            "plans": verified_plans
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
