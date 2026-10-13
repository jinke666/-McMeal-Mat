"""回归测试：普通推荐与多人推荐不得擅自领取优惠券。"""

import unittest

from mcmeal.agent import McMealAgent
from mcmeal.memory import McMealMemory
from mcmeal.mcp_client import DEFAULT_MENU_ITEMS
from mcmeal.models import DataReliability, MemberPreference, StoreInfo


class ReadOnlyCouponClient:
    """为测试提供稳定数据，并记录是否触发有副作用的领券操作。"""

    def __init__(self):
        self.auto_bind_calls = 0

    def auto_bind_coupons(self):
        self.auto_bind_calls += 1
        return {"success": True, "message": "测试领券"}

    def get_available_coupons(self):
        return []

    def get_campaign_calendar(self):
        return {}

    def query_nearby_stores(self, city="上海", keyword="人民广场"):
        return [
            StoreInfo(
                store_code="TEST",
                be_code=None,
                store_name="测试门店",
                address="测试地址",
                distance=0,
                reservation=True,
            )
        ]

    def get_store_meals(self, store_code="TEST"):
        return DEFAULT_MENU_ITEMS

    def calculate_price(self, items, coupon_ids=None, discount_deduction=0.0, store_code=None):
        original = sum(item.original_price for item in items)
        payable = max(0.0, sum(item.price for item in items) - discount_deduction)
        return {
            "original_amount": round(original, 2),
            "payable_amount": round(payable, 2),
            "reliability": DataReliability.ESTIMATED,
        }


class TestLowFrictionSafety(unittest.TestCase):
    def setUp(self):
        self.client = ReadOnlyCouponClient()
        self.memory = McMealMemory(db_path=":memory:")
        self.agent = McMealAgent(mcp_client=self.client, memory=self.memory)

    def tearDown(self):
        self.memory.close()

    def test_single_meal_recommendation_does_not_claim_coupons(self):
        result = self.agent.process_request(
            "预算25元，想吃汉堡和饮料",
            user_id="low-friction-test",
        )
        self.assertEqual(self.client.auto_bind_calls, 0)
        self.assertIn("未自动领取", result["coupon_status"])

    def test_group_recommendation_does_not_claim_coupons(self):
        members = [
            MemberPreference(name="A", budget=30.0),
            MemberPreference(name="B", budget=30.0),
        ]
        result = self.agent.process_group_order(members)
        self.assertEqual(self.client.auto_bind_calls, 0)
        self.assertIn("未自动领取", result["coupon_status"])


if __name__ == "__main__":
    unittest.main()
