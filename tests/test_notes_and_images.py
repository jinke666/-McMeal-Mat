import unittest
import os
import shutil
import tempfile
from mcmeal.agent import McMealAgent
from mcmeal.models import FoodCategory, OptimizationConstraint
from mcmeal.mcp_client import McDonaldMCPClient, DEFAULT_MENU_ITEMS
from mcmeal.memory import McMealMemory

class TestNotesAndImages(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_notes.db")
        self.memory = McMealMemory(db_path=self.db_path)
        self.agent = McMealAgent(memory=self.memory)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_menu_items_have_valid_images(self):
        """测试基准菜单项均配备官方麦当劳 CDN 图片地址"""
        for item in DEFAULT_MENU_ITEMS:
            self.assertTrue(item.image_url.startswith("http"), f"{item.name} 缺少有效图片 URL")
            self.assertIn("mcd.cn", item.image_url)

    def test_get_store_meals_preserves_images(self):
        """测试离线/在线菜单获取均能完整传递 image_url"""
        client = McDonaldMCPClient()
        meals = client.get_store_meals()
        for meal in meals:
            self.assertTrue(meal.image_url.startswith("http"), f"{meal.name} 在 get_store_meals 中丢失图片 URL")

    def test_parse_custom_notes_and_allergies(self):
        """测试自然语言精准解析去冰、去酸黄瓜及忌口要求"""
        query = "预算35，想要可乐少冰，汉堡去酸黄瓜，不吃辣，对牛奶过敏"
        constraint = self.agent._parse_intent(query)

        self.assertIn("少冰", constraint.custom_notes)
        self.assertIn("去酸黄瓜", constraint.custom_notes)
        self.assertFalse(constraint.is_spicy_ok)
        self.assertIn("纯牛奶（盒装）", constraint.excluded_items)
        self.assertIn("奥利奥麦旋风", constraint.excluded_items)

    def test_notes_attached_to_plan_items(self):
        """测试客制化制作备注准确应用至对应类别的餐品与方案"""
        res = self.agent.process_request("预算 30 元，想吃汉堡和饮料，可乐去冰，汉堡去酸黄瓜", user_id="user_test_2")
        plans = res.get("plans", [])
        self.assertTrue(len(plans) > 0)
        top_plan = plans[0]

        # 检查是否记录客制化备注
        self.assertTrue(any("去冰" in note for note in top_plan.dietary_notes))
        # 检查餐品对象中的 customizations 列表
        drink_items = [i for i in top_plan.items if i.category == FoodCategory.DRINK]
        for d in drink_items:
            self.assertIn("去冰", d.customizations)

    def test_memory_persistence_of_custom_notes(self):
        """测试用户的客制化备注可被持久化到长期记忆并在下一轮自动复用"""
        self.agent.process_request("给我配个汉堡套餐，可乐去冰", user_id="user_ice_lover")
        
        # 验证记忆库已存入去冰偏好
        pref = self.memory.get_preference("user_ice_lover", "drink_ice_note")
        self.assertIsNotNone(pref)
        self.assertEqual(pref.value, "去冰")

        # 新会话不显式提去冰，测试自动继承
        res2 = self.agent.process_request("预算25想要汉堡和饮料", user_id="user_ice_lover")
        self.assertTrue(len(res2["plans"]) > 0)
        top_plan = res2["plans"][0]
        self.assertTrue(any("去冰" in note for note in top_plan.dietary_notes))

    def test_markdown_format_renders_images_and_notes(self):
        """测试格式化 Markdown 表格包含官方图片 HTML 标签与备注"""
        res = self.agent.process_request("预算 30 元，可乐去冰", user_id="user_md_test")
        plan = res["plans"][0]
        md = self.agent.format_plan_markdown(plan)

        self.assertIn("<img src=", md)
        self.assertIn("https://menu-img.mcd.cn", md)
        self.assertIn("去冰", md)

    def test_markdown_list_renders_markdown_image_tags(self):
        """测试清单格式输出标准 Markdown 图片语法 ![name](url)"""
        res = self.agent.process_request("预算 30 元，可乐去冰", user_id="user_list_test")
        plan = res["plans"][0]
        md_list = self.agent.format_plan_markdown_list(plan)

        self.assertIn("![", md_list)
        self.assertIn("https://menu-img.mcd.cn", md_list)
        self.assertIn("去冰", md_list)

    def test_vague_prompt_does_not_hijack_decision(self):
        """测试当用户发出模糊问候时（如'我要点麦当劳'），麦麦提供启发引导，不越权直接下单"""
        res = self.agent.process_request("我要点麦当劳", user_id="user_vague_test")
        speech = res.get("maimai_speech", "")
        self.assertIn("好呀！今天想吃汉堡、炸鸡还是健康轻食？", speech)
        self.assertIn("挑选了两套可比较的方案", speech)
        self.assertNotIn("说一声我就去下单", speech)

    def test_reorder_prompt_provides_flavor_comparison(self):
        """测试当用户说'重新点'时，麦麦提供新口味对比，不盲目固定旧方案"""
        res = self.agent.process_request("重新点", user_id="user_reorder_test")
        speech = res.get("maimai_speech", "")
        self.assertIn("收到！这次想换个什么口味？", speech)
        self.assertIn("两套新方向的对比方案", speech)

if __name__ == "__main__":
    unittest.main()
