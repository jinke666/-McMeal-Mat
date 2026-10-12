"""
McMealMemory 模块单元测试
验证偏好持久化、来源标签识别、透明查看、遗忘权擦除与历史订单记录
"""

import unittest
from mcmeal.memory import McMealMemory, UserPreference

class TestMcMealMemory(unittest.TestCase):
    def setUp(self):
        # 使用内存 SQLite 数据库避免文件污染
        self.memory = McMealMemory(db_path=":memory:")
        self.user_id = "test_user_001"

    def test_set_and_get_preference(self):
        # 1. 设置偏好 (user-stated)
        self.memory.set_preference(self.user_id, "spicy_ok", "false", source="user-stated")
        pref = self.memory.get_preference(self.user_id, "spicy_ok")
        self.assertIsNotNone(pref)
        self.assertEqual(pref.value, "false")
        self.assertEqual(pref.source, "user-stated")

        # 2. 更新偏好 (system-inferred)
        self.memory.set_preference(self.user_id, "spicy_ok", "true", source="system-inferred")
        updated = self.memory.get_preference(self.user_id, "spicy_ok")
        self.assertEqual(updated.value, "true")
        self.assertEqual(updated.source, "system-inferred")

    def test_list_preferences(self):
        self.memory.set_preference(self.user_id, "fav_item", "双层吉士汉堡", source="user-stated")
        self.memory.set_preference(self.user_id, "budget_limit", "30", source="user-stated")
        self.memory.set_preference(self.user_id, "dietary_goal", "low_fat", source="system-inferred")

        prefs = self.memory.list_preferences(self.user_id)
        self.assertEqual(len(prefs), 3)
        keys = {p.key for p in prefs}
        self.assertEqual(keys, {"fav_item", "budget_limit", "dietary_goal"})

    def test_erase_preference_specific_key(self):
        self.memory.set_preference(self.user_id, "k1", "v1")
        self.memory.set_preference(self.user_id, "k2", "v2")

        deleted = self.memory.erase_preferences(self.user_id, key="k1")
        self.assertEqual(deleted, 1)

        self.assertIsNone(self.memory.get_preference(self.user_id, "k1"))
        self.assertIsNotNone(self.memory.get_preference(self.user_id, "k2"))

    def test_erase_all_preferences(self):
        self.memory.set_preference(self.user_id, "k1", "v1")
        self.memory.set_preference(self.user_id, "k2", "v2")

        deleted = self.memory.erase_preferences(self.user_id)
        self.assertEqual(deleted, 2)
        self.assertEqual(len(self.memory.list_preferences(self.user_id)), 0)

    def test_order_history_and_clear(self):
        order_id = self.memory.record_order(
            user_id=self.user_id,
            plan_name="麦门省钱王",
            total_amount=13.9,
            items_summary="双层吉士汉堡 + 阳光柠檬红茶"
        )
        self.assertGreater(order_id, 0)

        history = self.memory.get_order_history(self.user_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].plan_name, "麦门省钱王")
        self.assertEqual(history[0].total_amount, 13.9)

        # 清除全部数据
        self.memory.clear_all_data(self.user_id)
        self.assertEqual(len(self.memory.get_order_history(self.user_id)), 0)

    def test_prompt_context_summary(self):
        self.memory.set_preference(self.user_id, "spicy_ok", "false", source="user-stated")
        self.memory.set_preference(self.user_id, "frequent_snack", "麦乐鸡", source="system-inferred")

        context = self.memory.get_context_for_prompt(self.user_id)
        self.assertIn("用户记忆与长期偏好", context)
        self.assertIn("spicy_ok: false (用户设定)", context)
        self.assertIn("frequent_snack: 麦乐鸡 (系统推断)", context)

if __name__ == "__main__":
    unittest.main()
