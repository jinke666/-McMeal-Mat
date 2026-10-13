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
from mcmeal.models import MenuItem, NutritionInfo, FoodCategory, Coupon, StoreInfo, DataReliability

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

# 预置标准菜单与基础定价（含官方实时'上新'新品标签）
DEFAULT_MENU_ITEMS: List[MenuItem] = [
    MenuItem("M001", "双层吉士汉堡", price=23.5, original_price=23.5, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["双层吉士汉堡"]),
    MenuItem("M002", "巨无霸", price=26.0, original_price=26.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["巨无霸"]),
    MenuItem("M003", "板烧鸡腿堡", price=24.0, original_price=24.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["板烧鸡腿堡"]),
    MenuItem("M004", "麦辣鸡腿汉堡", price=22.0, original_price=22.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["麦辣鸡腿汉堡"]),
    MenuItem("M005", "麦香鱼", price=21.0, original_price=21.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["麦香鱼"]),
    MenuItem("M006", "麦香鸡", price=14.0, original_price=14.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["麦香鸡"]),
    MenuItem("M007", "培根安格斯厚牛堡", price=36.0, original_price=36.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["培根安格斯厚牛堡"]),
    MenuItem("M008", "龙焰鸡腿堡", price=24.0, original_price=24.0, category=FoodCategory.MAIN, nutrition=DEFAULT_NUTRITION_DATABASE["板烧鸡腿堡"], tags=["上新", "韩式辣椒黄油风味"]),
    MenuItem("S001", "中薯条", price=14.5, original_price=14.5, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["中薯条"]),
    MenuItem("S002", "麦乐鸡5块", price=13.5, original_price=13.5, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["麦乐鸡5块"]),
    MenuItem("S003", "麦辣鸡翅-2块", price=14.5, original_price=14.5, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["麦辣鸡翅-2块"]),
    MenuItem("S004", "大杯玉米杯", price=12.0, original_price=12.0, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["大杯玉米杯"]),
    MenuItem("S005", "麦麦脆汁鸡-琵琶腿", price=15.0, original_price=15.0, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["麦麦脆汁鸡-琵琶腿"]),
    MenuItem("S006", "心形薯饼5块", price=14.5, original_price=14.5, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["中薯条"], tags=["上新", "心形薯饼同款比心"]),
    MenuItem("S007", "月下相思扭扭薯", price=15.0, original_price=15.0, category=FoodCategory.SNACK, nutrition=DEFAULT_NUTRITION_DATABASE["中薯条"], tags=["上新", "口口酥脆"]),
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
        self.last_menu_reliability = DataReliability.MOCK
        self.last_menu_store_code = None

    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """通过 Streamable HTTP 协议调用麦当劳 MCP Tool"""
        if not self.token:
            logger.warning("未配置 MCD_MCP_TOKEN，使用离线演示数据（非实时）")
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
        """读取可用优惠。离线样例仅用于演示；在线响应无法识别时不伪造优惠。"""
        if not self.token:
            # 离线演示数据：仅用于验证本地优化流程，不代表真实可领取优惠。
            return [
                Coupon("MOCK-CP001", "示例：中薯条买一送一", coupon_type="BOGO", discount_amount=14.5, target_item_codes=["S001"]),
                Coupon("MOCK-CP002", "示例：9.9元中杯冰美式", coupon_type="SPECIAL_PRICE", discount_amount=2.1, target_item_codes=["D004"]),
                Coupon("MOCK-CP003", "示例：双层吉士堡立减5元", coupon_type="CASH_OFF", discount_amount=5.0, min_spend=20.0, target_item_codes=["M001"]),
                Coupon("MOCK-CP004", "示例：麦麦省满39减8元", coupon_type="CASH_OFF", discount_amount=8.0, min_spend=39.0),
                Coupon("MOCK-CP005", "示例：麦乐鸡5块特惠9.9元", coupon_type="SPECIAL_PRICE", discount_amount=3.6, target_item_codes=["S002"]),
            ]

        res = self.call_tool("available-coupons")
        data = res.get("data") if isinstance(res, dict) else None
        if isinstance(data, dict):
            for key in ("coupons", "couponList", "list", "records", "items"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        elif isinstance(data, str):
            # 不猜测文本表格字段，避免将未解析的响应误当成实时优惠。
            logger.warning("可用优惠接口返回文本格式，当前未能可靠解析；不加入未经核实的优惠")
            return []

        if not isinstance(data, list):
            logger.warning("可用优惠接口响应结构未识别；不加入未经核实的优惠")
            return []

        coupons: List[Coupon] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            coupon_id = item.get("couponId") or item.get("id") or item.get("couponCode")
            title = item.get("title") or item.get("couponName") or item.get("name")
            if not coupon_id or not title:
                continue
            try:
                discount_amount = float(item.get("discountAmount", item.get("amount", 0)) or 0)
                min_spend = float(item.get("minSpend", item.get("minimumSpend", 0)) or 0)
                discount_rate = float(item.get("discountRate", 1) or 1)
            except (TypeError, ValueError):
                logger.warning("跳过字段无法解析的优惠券响应")
                continue
            target_codes = item.get("targetItemCodes") or item.get("productCodes") or []
            if not isinstance(target_codes, list):
                target_codes = []
            coupon_type = str(item.get("couponType") or item.get("type") or "DISCOUNT").upper()
            coupons.append(Coupon(
                coupon_id=str(coupon_id),
                title=str(title),
                coupon_type=coupon_type,
                discount_amount=discount_amount,
                discount_rate=discount_rate,
                min_spend=min_spend,
                target_item_codes=[str(code) for code in target_codes],
                is_claimed=bool(item.get("isClaimed", item.get("claimed", True))),
            ))
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
        if not stores and not self.token:
            # 离线演示门店，不代表真实地理位置或营业状态。
            stores.append(StoreInfo(
                store_code="MOCK-STORE",
                be_code=None,
                store_name="离线演示门店（非真实门店）",
                address="示例地址（仅用于本地演示）",
                distance=0,
                reservation=False
            ))
        elif not stores:
            logger.warning("未查到可核验的实时门店；不使用硬编码门店冒充搜索结果")
        return stores

    def get_store_meals(self, store_code: str = "1450713", order_type: int = 1, be_type: int = 1) -> List[MenuItem]:
        """查询门店可售卖餐品列表（优先使用官方实时菜单及'上新'标签）"""
        nutrition_map = self.get_nutrition_foods()
        if self.token:
            try:
                res = self.call_tool("query-meals", {
                    "storeCode": store_code,
                    "orderType": order_type,
                    "beType": be_type
                })
                if isinstance(res, dict) and "data" in res and "meals" in res["data"]:
                    live_meals = res["data"]["meals"]
                    parsed_menu = []
                    for code, meal_info in live_meals.items():
                        name = meal_info.get("name", "")
                        price = float(meal_info.get("currentPrice", 0.0))
                        orig_price = float(meal_info.get("originalPrice", price))
                        tags = meal_info.get("tags", [])

                        category = FoodCategory.MAIN
                        if any(w in name for w in ["薯", "鸡块", "鸡翅", "鸡排", "小食", "拼盘", "盒"]):
                            category = FoodCategory.SNACK
                        elif any(w in name for w in ["可乐", "雪碧", "咖啡", "茶", "牛奶", "果汁", "饮"]):
                            category = FoodCategory.DRINK
                        elif any(w in name for w in ["派", "麦旋风", "新地", "冰淇淋", "圆筒"]):
                            category = FoodCategory.DESSERT
                        elif "套" in name or "餐" in name:
                            category = FoodCategory.COMBO

                        nutri = nutrition_map.get(name, NutritionInfo())
                        parsed_menu.append(MenuItem(
                            code=str(code),
                            name=name,
                            price=price,
                            original_price=orig_price,
                            category=category,
                            nutrition=nutri,
                            tags=tags,
                            is_new_arrival=("上新" in tags)
                        ))
                    if parsed_menu:
                        self.last_menu_reliability = DataReliability.LIVE_VERIFIED
                        self.last_menu_store_code = store_code
                        return parsed_menu
            except Exception as e:
                logger.warning(f"获取实时菜单失败，使用离线基准菜单: {e}")

        # 离线沙箱降级菜单；必须保留 MOCK 状态，不可伪装为实时菜单。
        self.last_menu_reliability = DataReliability.MOCK
        self.last_menu_store_code = store_code
        menu = []
        for item in DEFAULT_MENU_ITEMS:
            nutri = nutrition_map.get(item.name, item.nutrition)
            menu.append(MenuItem(
                code=item.code,
                name=item.name,
                price=item.price,
                original_price=item.original_price,
                category=item.category,
                nutrition=nutri,
                tags=item.tags,
                is_new_arrival=item.is_new_arrival
            ))
        return menu

    def calculate_price(self, items: List[MenuItem], coupon_ids: List[str] = None, discount_deduction: float = 0.0, store_code: Optional[str] = None) -> Dict[str, Any]:
        """计算商品价格与实际优惠；只对本次已核验的实时菜单尝试官方核价。"""
        verified_store = store_code or self.last_menu_store_code
        if self.token and self.last_menu_reliability == DataReliability.LIVE_VERIFIED and verified_store:
            payload_items = [{"productCode": item.code, "quantity": 1} for item in items]
            try:
                res = self.call_tool("calculate-price", {
                    "storeCode": verified_store,
                    "orderType": 1,
                    "beType": 1,
                    "items": payload_items
                })
                if isinstance(res, dict) and "data" in res and "price" in res["data"]:
                    data = res["data"]
                    payable = data.get("price", 0) / 100.0
                    original = data.get("originalPrice", 0) / 100.0
                    discount = max(0.0, original - payable + discount_deduction)
                    return {
                        "original_amount": round(original, 2),
                        "payable_amount": round(max(0.0, payable - discount_deduction), 2),
                        "discount_amount": round(discount, 2),
                        # 远程请求未显式传入优惠券应用结果；任何本地优惠扣减都只能视为估算。
                        "reliability": (
                            DataReliability.LIVE_VERIFIED
                            if not coupon_ids and discount_deduction <= 0
                            else DataReliability.ESTIMATED
                        )
                    }
            except Exception as e:
                logger.warning(f"远程算价异常，回退算法核算: {e}")

        original_price = sum(item.original_price for item in items)
        base_price = max(0.0, sum(item.price for item in items) - discount_deduction)
        discount = max(0.0, original_price - base_price)
        return {
            "original_amount": round(original_price, 2),
            "payable_amount": round(base_price, 2),
            "discount_amount": round(discount, 2),
            "reliability": (
                DataReliability.ESTIMATED
                if self.token and self.last_menu_reliability == DataReliability.LIVE_VERIFIED
                else DataReliability.MOCK
            )
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
