"""
数据模型单元测试
"""

import unittest
from mcmeal.models import NutritionInfo, MenuItem, FoodCategory, Coupon, OptimizationConstraint

class TestModels(unittest.TestCase):

    def test_nutrition_addition(self):
        n1 = NutritionInfo(energy_kj=1000, energy_kcal=240, protein=15, fat=10, carbohydrate=25, sodium=500, calcium=100)
        n2 = NutritionInfo(energy_kj=500, energy_kcal=120, protein=5, fat=2, carbohydrate=20, sodium=100, calcium=50)
        n3 = n1 + n2
        self.assertEqual(n3.energy_kcal, 360)
        self.assertEqual(n3.protein, 20)
        self.assertEqual(n3.fat, 12)
        self.assertEqual(n3.sodium, 600)

    def test_menu_item_defaults(self):
        item = MenuItem(code="T001", name="测试汉堡", price=20.0)
        self.assertEqual(item.original_price, 20.0)
        self.assertEqual(item.category, FoodCategory.MAIN)
        self.assertTrue(item.is_available)

    def test_coupon_properties(self):
        cp = Coupon(coupon_id="CP1", title="满30减5", discount_amount=5.0, min_spend=30.0)
        self.assertEqual(cp.coupon_type, "DISCOUNT")
        self.assertEqual(cp.discount_amount, 5.0)
        self.assertEqual(cp.min_spend, 30.0)

if __name__ == "__main__":
    unittest.main()
