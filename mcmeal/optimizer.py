"""
麦门运筹学核心优化求解引擎 (McKnapsack Optimizer)
基于多约束背包问题、动态规划与组合优化算法实现极致省钱与餐品推荐
"""

from typing import List, Dict, Optional, Tuple
import itertools
from mcmeal.models import (
    MenuItem, NutritionInfo, FoodCategory, Coupon,
    OptimizationConstraint, OptimizedPlan
)
from mcmeal.mcp_client import RED_ZONE_ITEMS, WHITE_ZONE_ITEMS

class McOptimizer:
    """麦当劳配餐多约束运筹优化器"""

    def __init__(self, menu: List[MenuItem], coupons: List[Coupon] = None):
        self.menu = menu
        self.coupons = coupons or []
        self._item_map = {item.name: item for item in menu}
        self._code_map = {item.code: item for item in menu}

    def solve(self, constraint: OptimizationConstraint) -> List[OptimizedPlan]:
        """
        根据给定的预算、营养、品类等约束，求解最优配餐方案
        返回 Top 3 差异化候选方案（省钱王、均衡结构、高蛋白低卡）
        """
        # 1. 过滤忌口与不可用餐品
        valid_menu = [
            item for item in self.menu
            if item.is_available and item.name not in constraint.excluded_items
        ]

        # 2. 生成所有候选可行基础组合（含随心配 1+1 虚拟组合 + 单点组合）
        candidate_combinations = self._generate_candidate_meals(valid_menu, constraint)

        if not candidate_combinations:
            # 降级宽松策略，至少生成兜底保障方案
            candidate_combinations = self._generate_fallback_meals(valid_menu, constraint)

        # 3. 为每个组合核算优惠券折抵、总原价、实际总价、营养数据
        evaluated_plans: List[OptimizedPlan] = []
        for items, combo_type in candidate_combinations:
            plan = self._evaluate_combination(items, combo_type, constraint)
            if plan and plan.actual_total <= constraint.max_budget:
                evaluated_plans.append(plan)

        if not evaluated_plans:
            # 允许超出极微小公差的方案以防无解
            for items, combo_type in candidate_combinations[:10]:
                plan = self._evaluate_combination(items, combo_type, constraint)
                if plan:
                    evaluated_plans.append(plan)

        # 4. 多目标分选策略
        return self._rank_and_select_top_plans(evaluated_plans, constraint)

    def optimize_delivery_pooling(self, current_items: List[MenuItem], min_spend: float = 39.0) -> Tuple[List[MenuItem], float, str]:
        """
        拼单免外送费最优凑单算法 (Delivery Threshold Pooling)
        当总价未达到免配/起送门槛时，寻找最贴近差额且性价比最高的凑单小食/饮品
        """
        current_total = sum(i.price for i in current_items)
        shortage = min_spend - current_total
        if shortage <= 0:
            return [], 0.0, "当前订单已达到免外送费起送门槛，无需凑单！"

        candidates = [
            item for item in self.menu
            if item.category in (FoodCategory.SNACK, FoodCategory.DRINK, FoodCategory.DESSERT)
        ]

        best_additions: List[MenuItem] = []
        min_waste = float("inf")
        best_explanation = ""

        # 单品凑单搜索
        for item in candidates:
            if item.price >= shortage:
                waste = item.price - shortage
                if waste < min_waste:
                    min_waste = waste
                    best_additions = [item]
                    best_explanation = f"添加单品【{item.name}】（¥{item.price:.1f}），刚刚满足 ¥{min_spend:.1f} 门槛，溢出仅 ¥{waste:.1f}"

        # 双品凑单搜索
        for i, item1 in enumerate(candidates):
            for item2 in candidates[i:]:
                combined_price = item1.price + item2.price
                if combined_price >= shortage:
                    waste = combined_price - shortage
                    if waste < min_waste:
                        min_waste = waste
                        best_additions = [item1, item2]
                        best_explanation = f"组合添加【{item1.name}】+【{item2.name}】（共 ¥{combined_price:.1f}），最优卡位起送门槛，仅超出 ¥{waste:.1f}"

        return best_additions, min_waste, best_explanation

    def _generate_candidate_meals(self, menu: List[MenuItem], constraint: OptimizationConstraint) -> List[Tuple[List[MenuItem], str]]:
        """构建候选组合集合（融合 1+1 随心配与单品组合）"""
        results: List[Tuple[List[MenuItem], str]] = []

        # A. 提取 1+1 随心配组合 (红区 + 白区 = 13.9 元)
        red_items = [item for item in menu if item.name in RED_ZONE_ITEMS]
        white_items = [item for item in menu if item.name in WHITE_ZONE_ITEMS]

        combos_1plus1 = []
        for r in red_items:
            for w in white_items:
                # 虚拟化 1+1 项目（打包原价为原价和，售价记为 13.9）
                combos_1plus1.append(([r, w], "1+1随心配"))

        # B. 组合扩展：1+1 随心配 + 1份主食/小食 (适合 20-35 元预算)
        other_mains = [item for item in menu if item.category == FoodCategory.MAIN and item.name not in RED_ZONE_ITEMS]
        other_snacks = [item for item in menu if item.category == FoodCategory.SNACK]

        for combo, _ in combos_1plus1:
            results.append((combo, "1+1经典随心配"))
            for extra in (other_mains + other_snacks):
                results.append((combo + [extra], "随心配+甄选加餐"))

        # C. 经典三件套 (主食 + 小食 + 饮品)
        mains = [i for i in menu if i.category == FoodCategory.MAIN]
        snacks = [i for i in menu if i.category == FoodCategory.SNACK]
        drinks = [i for i in menu if i.category == FoodCategory.DRINK]

        for m in mains:
            for s in snacks:
                for d in drinks:
                    results.append(([m, s, d], "经典丰盛三件套"))

        # D. 双主食大快朵颐餐 (主食 + 主食 + 饮品)
        for m1 in mains:
            for m2 in mains:
                if m1.code <= m2.code:
                    for d in drinks:
                        results.append(([m1, m2, d], "双堡能量双拼套餐"))

        return results

    def _generate_fallback_meals(self, menu: List[MenuItem], constraint: OptimizationConstraint) -> List[Tuple[List[MenuItem], str]]:
        """极端低预算或苛刻条件下的保底组合生成"""
        cheapest_main = min([i for i in menu if i.category == FoodCategory.MAIN], key=lambda x: x.price, default=menu[0])
        cheapest_drink = min([i for i in menu if i.category == FoodCategory.DRINK], key=lambda x: x.price, default=menu[0])
        return [([cheapest_main, cheapest_drink], "极简护航套餐")]

    def _evaluate_combination(self, items: List[MenuItem], combo_type: str, constraint: OptimizationConstraint) -> Optional[OptimizedPlan]:
        """评估单个组合的原价、实付金额、优惠券减免、营养健康度"""
        original_total = sum(i.original_price for i in items)
        base_price = sum(i.price for i in items)

        # 检查是否包含随心配
        has_1plus1 = False
        if combo_type.startswith("1+1") or combo_type.startswith("随心配"):
            has_1plus1 = True
            # 计算 1+1 随心配节省额度
            # 正常红白区单点原价至少 24+10=34，随心配统一一口价 13.9
            # 这里扣减红区第一项和白区第一项差价
            r_item = next((i for i in items if i.name in RED_ZONE_ITEMS), None)
            w_item = next((i for i in items if i.name in WHITE_ZONE_ITEMS), None)
            if r_item and w_item:
                regular_price = r_item.price + w_item.price
                discount_1plus1 = regular_price - 13.9
                base_price = max(13.9, base_price - discount_1plus1)

        # 应用优惠券
        applied_coupons: List[Coupon] = []
        total_discount = original_total - base_price

        # 尝试匹配单品特惠券或满减券
        for coupon in self.coupons:
            if coupon.min_spend > 0 and base_price < coupon.min_spend:
                continue
            
            # 单品券匹配
            if coupon.target_item_codes:
                matched = any(i.code in coupon.target_item_codes for i in items)
                if matched:
                    base_price = max(0.0, base_price - coupon.discount_amount)
                    applied_coupons.append(coupon)
                    break
            elif coupon.discount_amount > 0 and not applied_coupons:
                # 满减券
                base_price = max(0.0, base_price - coupon.discount_amount)
                applied_coupons.append(coupon)
                break

        actual_total = round(base_price, 2)
        saved_amount = round(original_total - actual_total, 2)
        discount_rate = round(actual_total / original_total, 2) if original_total > 0 else 1.0

        # 计算总营养
        total_nutrition = NutritionInfo()
        for i in items:
            total_nutrition = total_nutrition + i.nutrition

        # 校验卡路里与宏量营养素约束
        if constraint.max_calories and total_nutrition.energy_kcal > constraint.max_calories:
            return None
        if constraint.min_protein and total_nutrition.protein < constraint.min_protein:
            return None
        if constraint.max_sodium and total_nutrition.sodium > constraint.max_sodium:
            return None

        # 校验必选品类约束
        present_categories = {i.category for i in items}
        for req_cat in constraint.required_categories:
            if req_cat not in present_categories:
                return None

        # 校验用户必点
        if constraint.preferred_items:
            names = [i.name for i in items]
            if not all(p in names for p in constraint.preferred_items):
                return None

        return OptimizedPlan(
            plan_name=combo_type,
            items=items,
            original_total=round(original_total, 2),
            actual_total=actual_total,
            saved_amount=saved_amount,
            discount_rate=discount_rate,
            total_nutrition=total_nutrition,
            applied_coupons=applied_coupons
        )

    def _rank_and_select_top_plans(self, plans: List[OptimizedPlan], constraint: OptimizationConstraint) -> List[OptimizedPlan]:
        """根据多目标维度智能挑选三大特色代表方案"""
        if not plans:
            return []

        # 去重相同餐品名单
        unique_plans: Dict[str, OptimizedPlan] = {}
        for p in plans:
            key = "-".join(sorted(i.name for i in p.items))
            if key not in unique_plans or p.actual_total < unique_plans[key].actual_total:
                unique_plans[key] = p
        distinct_plans = list(unique_plans.values())

        # 1. 方案 A：极致省钱王 (折扣力度最大 / 立省最多)
        plan_savings = max(distinct_plans, key=lambda p: (p.saved_amount, -p.actual_total))
        plan_savings.plan_name = "🥇【麦门省钱王】极致优惠组合"
        plan_savings.explanation = f"利用 1+1 随心配及优惠券深度杠杆，原价 ¥{plan_savings.original_total}，实付仅需 ¥{plan_savings.actual_total}，立省 ¥{plan_savings.saved_amount} (相当于 {plan_savings.discount_rate*10:.1f} 折)！"

        # 2. 方案 B：黄金饱腹均衡餐 (蛋白质适中，主食+小食+饮品齐全)
        balanced_candidates = [
            p for p in distinct_plans
            if any(i.category == FoodCategory.MAIN for i in p.items)
            and any(i.category == FoodCategory.DRINK for i in p.items)
            and any(i.category in (FoodCategory.SNACK, FoodCategory.DESSERT) for i in p.items)
        ]
        if not balanced_candidates:
            balanced_candidates = distinct_plans
        plan_balanced = min(balanced_candidates, key=lambda p: abs(p.actual_total - (constraint.max_budget * 0.85)))
        plan_balanced.plan_name = "🥈【营养金字塔】经典均衡套餐"
        plan_balanced.explanation = f"涵盖汉堡主食、小食与解腻饮品，提供 {plan_balanced.total_nutrition.protein:.0f}g 优质蛋白，实付 ¥{plan_balanced.actual_total}，饱腹感十足。"

        # 3. 方案 C：极客轻断食/低卡高蛋白餐 (热量最低或单位热量蛋白质最高)
        plan_fit = min(distinct_plans, key=lambda p: (p.total_nutrition.energy_kcal / max(1.0, p.total_nutrition.protein)))
        plan_fit.plan_name = "🥉【极客控卡伴侣】高蛋白低负担餐"
        plan_fit.explanation = f"总热量严格控制在 {plan_fit.total_nutrition.energy_kcal:.0f} kcal 内，含有 {plan_fit.total_nutrition.protein:.0f}g 蛋白质，久坐敲代码不犯困、身材管理首选！"

        selected = [plan_savings]
        if plan_balanced not in selected:
            selected.append(plan_balanced)
        if plan_fit not in selected:
            selected.append(plan_fit)

        return selected
