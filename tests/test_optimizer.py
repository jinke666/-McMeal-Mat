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

if __name__ == "__main__":
    unittest.main()
