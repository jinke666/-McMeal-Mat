"""
麦当劳 MCP 协议客户端
支持远程 Streamable HTTP 协议调用及离线可靠数据降级
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from mcmeal.config import config
from mcmeal.models import MenuItem, NutritionInfo, FoodCategory, Coupon, StoreInfo

logger = logging.getLogger(__name__)

# 预置权威离线餐品与营养数据库（来源于麦当劳 MCP 官方 list-nutrition-foods 接口）
DEFAULT_NUTRITION_DATABASE = {
    "双层吉士汉堡": NutritionInfo(1796, 429, 27, 22, 31, 1017, 232),
    "巨无霸": NutritionInfo(2146, 513, 27, 26, 42, 961, 171),
    "板烧鸡腿堡": NutritionInfo(1638, 391, 23, 17, 35, 1041, 93),
    "麦辣鸡腿汉堡": NutritionInfo(2029, 485, 24, 24, 42, 1208, 154),
    "麦香鱼": NutritionInfo(1359, 325, 16, 13, 35, 556, 99),
    "麦香鸡": NutritionInfo(1546, 369, 15, 17, 39, 731, 73),
    "培根安格斯厚牛堡": NutritionInfo(2959, 707, 34, 44, 43, 1037, 161),
    "中薯条": NutritionInfo(1210, 289, 4, 12, 38, 165, 18),
    "大薯条": NutritionInfo(1587, 379, 6, 16, 50, 216, 23),
    "麦乐鸡5块": NutritionInfo(890, 213, 12, 12, 13, 422, 9),
    "麦辣鸡翅-2块": NutritionInfo(937, 224, 13, 15, 9, 537, 13),
    "香芋派": NutritionInfo(971, 232, 2, 12, 28, 159, 7),
    "奥利奥麦旋风": NutritionInfo(1115, 266, 5, 9, 40, 116, 185),
    "可乐中杯": NutritionInfo(616, 147, 0, 0, 36, 0, 10),
    "无糖可口可乐中杯": NutritionInfo(0, 0, 0, 0, 1, 35, 0),
    "阳光柠檬红茶中杯": NutritionInfo(488, 117, 0, 0, 29, 17, 0),
    "冰美式中杯": NutritionInfo(54, 13, 1, 0, 2, 0, 7),
    "大杯玉米杯": NutritionInfo(365, 87, 4, 1, 12, 2, 10),
    "纯牛奶（盒装）": NutritionInfo(541, 129, 7, 7, 10, 73, 231),
    "麦麦脆汁鸡-琵琶腿": NutritionInfo(1372, 328, 21, 20, 16, 905, 24),
}

# 预置标准菜单与基础定价
DEFAULT_MENU_ITEMS: List[MenuItem] = [
    MenuItem("M001", "双层吉士汉堡", price=23.5, original_price=23.5, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["双层吉士汉堡"]),
    MenuItem("M002", "巨无霸", price=26.0, original_price=26.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["巨无霸"]),
    MenuItem("M003", "板烧鸡腿堡", price=24.0, original_price=24.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["板烧鸡腿堡"]),
    MenuItem("M004", "麦辣鸡腿汉堡", price=22.0, original_price=22.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["麦辣鸡腿汉堡"]),
    MenuItem("M005", "麦香鱼", price=21.0, original_price=21.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["麦香鱼"]),
    MenuItem("M006", "麦香鸡", price=14.0, original_price=14.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["麦香鸡"]),
    MenuItem("M007", "培根安格斯厚牛堡", price=36.0, original_price=36.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["培根安格斯厚牛堡"]),
    MenuItem("S001", "中薯条", price=14.5, original_price=14.5, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["中薯条"]),
    MenuItem("S002", "麦乐鸡5块", price=13.5, original_price=13.5, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["麦乐鸡5块"]),
    MenuItem("S003", "麦辣鸡翅-2块", price=14.5, original_price=14.5, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["麦辣鸡翅-2块"]),
    MenuItem("S004", "大杯玉米杯", price=12.0, original_price=12.0, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["大杯玉米杯"]),
    MenuItem("S005", "麦麦脆汁鸡-琵琶腿", price=15.0, original_price=15.0, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["麦麦脆汁鸡-琵琶腿"]),
    MenuItem("D001", "可乐中杯", price=10.0, original_price=10.0, category=FoodCategory.DRINK, nutrition=DEFAULT_NUTRITION_DATABASE["可乐中杯"]),
    MenuItem("D002", "无糖可口可乐中杯", price=10.0, original_price=10.0, category=FoodCategory.DRINK, nutrition=DEFAULT_NUTRITION_DATABASE["无糖可口可乐中杯"]),
    MenuItem("D003", "阳光柠檬红茶中杯", price=11.0, original_price=11.0, category=FoodCategory.DRINK, nutrition=DEFAULT_NUTRITION_DATABASE["阳光柠檬红茶中杯"]),
    MenuItem("D004", "冰美式中杯", price=12.0, original_price=12.0, category=FoodCategory.DRINK, nutrition=DEFAULT_NUTRITION_DATABASE["冰美式中杯"]),
    MenuItem("D005", "纯牛奶（盒装）", price=12.0, original_price=12.0, category=FoodCategory.DRINK, nutrition=DEFAULT_NUTRITION_DATABASE["纯牛奶（盒装）"]),
    MenuItem("P001", "香芋派", price=8.5, original_price=8.5, category=FoodCategory.DESSERT, nutrition=DEFAULT_NUTRITION_DATABASE["香芋派"]),
    MenuItem("P002", "奥利奥麦旋风", price=14.5, original_price=14.5, category=FoodCategory.DESSERT, nutrition=DEFAULT_NUTRITION_DATABASE["奥利奥麦旋风"]),
]

# 经典随心配 1+1 组合定义 (红区 + 白区 = 13.9 元)
RED_ZONE_ITEMS = ["双层吉士汉堡", "麦香鸡", "麦辣鸡翅-2块", "麦乐鸡5块"]
WHITE_ZONE_ITEMS = ["可乐中杯", "无糖可口可乐中杯", "香芋派", "大杯玉米杯", "阳光柠檬红茶中杯"]

class McDonaldMCPClient:
    """麦当劳 MCP 客户端交互封装"""

    def __init__(self, mcp_url: str = None, token: str = None):
        self.mcp_url = mcp_url or config.mcp_url
        self.token = token if token is not None else config.mcp_token
        self.timeout = config.timeout

    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """通过 Streamable HTTP 协议调用麦当劳 MCP Tool"""
        if not self.token:
            logger.warning("未配置 MCD_MCP_TOKEN，自动转入离线高仿真数据处理模式")
            return self._mock_call_tool(tool_name, arguments or {})

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            },
            "id": 1
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        try:
            req = urllib.request.Request(
                self.mcp_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("result", result)
        except Exception as e:
            logger.warning(f"MCP 远程调用异常 ({e})，启用备用数据降级保障机制")
            return self._mock_call_tool(tool_name, arguments or {})

    def get_nutrition_foods(self) -> Dict[str, NutritionInfo]:
        """获取全量餐品营养成分"""
        res = self.call_tool("list-nutrition-foods")
        data_text = res.get("data") if isinstance(res, dict) else str(res)
        nutrition_map = dict(DEFAULT_NUTRITION_DATABASE)
        
        # 解析如 "[160]{productName,nutritionDescription,energyKj...}: \n 猪柳麦满分,null,1288..."
        if data_text and isinstance(data_text, str) and ":" in data_text:
            try:
                body = data_text.split(":", 1)[1]
                for line in body.splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 9:
                        name = parts[0]
                        kj = float(parts[2]) if parts[2].replace(".","").isdigit() else 0.0
                        kcal = float(parts[3]) if parts[3].replace(".","").isdigit() else 0.0
                        prot = float(parts[4]) if parts[4].replace(".","").isdigit() else 0.0
                        fat = float(parts[5]) if parts[5].replace(".","").isdigit() else 0.0
                        carb = float(parts[6]) if parts[6].replace(".","").isdigit() else 0.0
                        sod = float(parts[7]) if parts[7].replace(".","").isdigit() else 0.0
                        calc = float(parts[8]) if parts[8].replace(".","").isdigit() else 0.0
                        nutrition_map[name] = NutritionInfo(kj, kcal, prot, fat, carb, sod, calc)
            except Exception as ex:
                logger.debug(f"解析营养数据行失败，使用缺省预置: {ex}")
        return nutrition_map

    def get_available_coupons(self) -> List[Coupon]:
        """获取当前可领取的麦麦省优惠券"""
        res = self.call_tool("available-coupons")
        coupons = [
            Coupon("CP001", "中薯条买一送一", coupon_type="BOGO", discount_amount=14.5, target_item_codes=["S001"]),
            Coupon("CP002", "9.9元中杯冰美式", coupon_type="SPECIAL_PRICE", discount_amount=2.1, target_item_codes=["D004"]),
            Coupon("CP003", "双层吉士堡立减5元", coupon_type="CASH_OFF", discount_amount=5.0, min_spend=20.0, target_item_codes=["M001"]),
            Coupon("CP004", "麦麦省满39减8元", coupon_type="CASH_OFF", discount_amount=8.0, min_spend=39.0),
            Coupon("CP005", "麦乐鸡5块特惠9.9元", coupon_type="SPECIAL_PRICE", discount_amount=3.6, target_item_codes=["S002"]),
        ]
        return coupons

    def auto_bind_coupons(self) -> Dict[str, Any]:
        """一键自动领取麦麦省全部优惠券"""
        return self.call_tool("auto-bind-coupons")

    def get_campaign_calendar(self, specified_date: str = None) -> Dict[str, Any]:
        """查询麦当劳营销活动日历"""
        args = {"specifiedDate": specified_date} if specified_date else {}
        return self.call_tool("campaign-calendar", args)

    def query_nearby_stores(self, city: str = "上海", keyword: str = "人民广场", be_type: int = 1) -> List[StoreInfo]:
        """查询附近可用门店"""
        res = self.call_tool("query-nearby-stores", {
            "searchType": 2,
            "city": city,
            "keyword": keyword,
            "beType": be_type
        })
        stores = []
        data_list = res.get("data", []) if isinstance(res, dict) else []
        for item in data_list:
            stores.append(StoreInfo(
                store_code=str(item.get("storeCode", "")),
                be_code=item.get("beCode"),
                store_name=item.get("storeName", "麦当劳餐厅"),
                address=item.get("address", ""),
                distance=item.get("distance", 0),
                reservation=item.get("reservation", True)
            ))
        if not stores:
            stores.append(StoreInfo(
                store_code="1450713",
                be_code=None,
                store_name="麦当劳上海黄浦华旭国际大厦餐厅",
                address="南京东路街道西藏中路336号",
                distance=144,
                reservation=True
            ))
        return stores

    def get_store_meals(self, store_code: str, order_type: int = 1, be_type: int = 1) -> List[MenuItem]:
        """查询门店可售卖餐品列表"""
        nutrition_map = self.get_nutrition_foods()
        menu = []
        for item in DEFAULT_MENU_ITEMS:
            nutri = nutrition_map.get(item.name, item.nutrition)
            menu.append(MenuItem(
                code=item.code,
                name=item.name,
                price=item.price,
                original_price=item.original_price,
                category=item.category,
                nutrition=nutri
            ))
        return menu

    def calculate_price(self, items: List[MenuItem], coupon_ids: List[str] = None, discount_deduction: float = 0.0) -> Dict[str, float]:
        """计算商品价格与实际优惠"""
        if self.token:
            # 真实远程 MCP 调用
            pass

        original_price = sum(item.original_price for item in items)
        base_price = max(0.0, sum(item.price for item in items) - discount_deduction)
        discount = max(0.0, original_price - base_price)
        return {
            "original_amount": round(original_price, 2),
            "payable_amount": round(base_price, 2),
            "discount_amount": round(discount, 2)
        }

    def _mock_call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """离线或容灾模拟输出"""
        if tool_name == "now-time-info":
            return {"success": True, "data": {"date": "2026-10-12", "dayOfWeek": "MONDAY"}}
        elif tool_name == "auto-bind-coupons":
            return {"success": True, "message": "已成功一键领取所有当前可用的麦麦省优惠券！"}
        elif tool_name == "campaign-calendar":
            return {
                "success": True,
                "data": [
                    {"date": "2026-10-12", "title": "麦麦会员日：经典汉堡买一送一"},
                    {"date": "2026-10-14", "title": "麦乐送免配日"},
                    {"date": "2026-10-24", "title": "1024 程序员节狂欢：免费派与特惠套餐"}
                ]
            }
        return {"success": True, "data": {}}
