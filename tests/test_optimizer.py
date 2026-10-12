"""
运筹优化器单元测试
"""

import unittest
from mcmeal.models import OptimizationConstraint, FoodCategory
from mcmeal.mcp_client import DEFAULT_MENU_ITEMS
from mcmeal.optimizer import McOptimizer

class TestOptimizer(unittest.TestCase):

    def setUp(self):
        self.optimizer = McOptimizer(menu=DEFAULT_MENU_ITEMS)

    def test_solve_budget_constraint(self):
        constraint = OptimizationConstraint(max_budget=25.0)
        plans = self.optimizer.solve(constraint)
        self.assertTrue(len(plans) > 0)
        for p in plans:
            self.assertLessEqual(p.actual_total, 25.0)
            self.assertGreater(p.saved_amount, 0.0)

    def test_solve_calorie_constraint(self):
        constraint = OptimizationConstraint(max_budget=35.0, max_calories=700.0)
        plans = self.optimizer.solve(constraint)
        self.assertTrue(len(plans) > 0)
        for p in plans:
            self.assertLessEqual(p.total_nutrition.energy_kcal, 700.0)

    def test_solve_delivery_pooling(self):
        cart = [DEFAULT_MENU_ITEMS[0]] # 23.5 元
        additions, waste, exp = self.optimizer.optimize_delivery_pooling(cart, min_spend=39.0)
        total_after = 23.5 + sum(i.price for i in additions)
        self.assertGreaterEqual(total_after, 39.0)
        self.assertLessEqual(waste, 5.0)

    def test_solve_group_order(self):
        from mcmeal.models import MemberPreference
        members = [
            MemberPreference(name="Alice", budget=35.0, is_spicy_ok=True),
            MemberPreference(name="Bob", budget=30.0, is_spicy_ok=False, excluded_items=["麦辣鸡腿汉堡"])
        ]
        group_plans = self.optimizer.solve_group_order(members)
        self.assertEqual(len(group_plans), 3)
        for gp in group_plans:
            self.assertEqual(len(gp.members), 2)
            # 校验全员分摊之和等于整单实付
            members_sum = sum(m.final_payable for m in gp.members)
            self.assertAlmostEqual(members_sum, gp.total_actual, delta=0.1)
            # 校验 Bob 的餐品中不含辣
            bob_share = next(m for m in gp.members if m.member_name == "Bob")
            for item in bob_share.individual_items:
                self.assertNotIn("麦辣", item.name)

if __name__ == "__main__":
    unittest.main()
