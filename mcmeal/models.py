"""
数据模型定义模块 (Models)
定义麦麦搭子中的餐品、营养素、优惠券、数据可信度及双人/多人协同点餐数据结构
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

class DataReliability(str, Enum):
    """数据可信度标记 (遵从 v1.0 真实性规范)"""
    LIVE_VERIFIED = "LIVE_VERIFIED"  # 实时调用官方 MCP 接口核验成功
    CACHED = "CACHED"                # 缓存数据，附带更新时间
    ESTIMATED = "ESTIMATED"          # 本地算法试算/估算
    MOCK = "MOCK"                    # 离线沙箱模拟数据

class FoodCategory(str, Enum):
    """餐品类别"""
    MAIN = "主食"          # 汉堡、卷类、麦满分
    SNACK = "小食"         # 薯条、麦乐鸡、鸡翅、鸡排
    DRINK = "饮品"         # 可乐、咖啡、红茶、奶铁、雪冰
    DESSERT = "甜品"       # 派、新地、麦旋风、冰淇淋
    COMBO = "套餐"         # 经典三件套、四件套、随心配

@dataclass
class NutritionInfo:
    """餐品营养成分"""
    energy_kj: float = 0.0
    energy_kcal: float = 0.0
    protein: float = 0.0      # 蛋白质 (g)
    fat: float = 0.0          # 脂肪 (g)
    carbohydrate: float = 0.0 # 碳水化合物 (g)
    sodium: float = 0.0       # 钠 (mg)
    calcium: float = 0.0      # 钙 (mg)

    def __add__(self, other: "NutritionInfo") -> "NutritionInfo":
        return NutritionInfo(
            energy_kj=self.energy_kj + other.energy_kj,
            energy_kcal=self.energy_kcal + other.energy_kcal,
            protein=self.protein + other.protein,
            fat=self.fat + other.fat,
            carbohydrate=self.carbohydrate + other.carbohydrate,
            sodium=self.sodium + other.sodium,
            calcium=self.calcium + other.calcium,
        )

@dataclass
class MenuItem:
    """餐品信息"""
    code: str
    name: str
    price: float
    original_price: float = 0.0
    category: FoodCategory = FoodCategory.MAIN
    nutrition: NutritionInfo = field(default_factory=NutritionInfo)
    description: str = ""
    image_url: str = ""
    is_available: bool = True
    tags: List[str] = field(default_factory=list)      # 官方标签，如 ["上新", "心形薯饼"]
    is_new_arrival: bool = False                       # 是否官方新品

    def __post_init__(self):
        if self.original_price <= 0:
            self.original_price = self.price
        if "上新" in self.tags:
            self.is_new_arrival = True

@dataclass
class Coupon:
    """优惠券信息"""
    coupon_id: str
    title: str
    coupon_type: str = "DISCOUNT"  # DISCOUNT, BOGO (买一送一), CASH_OFF, FREE
    discount_amount: float = 0.0   # 减免金额
    discount_rate: float = 1.0     # 折扣率 (0.8 = 8折)
    min_spend: float = 0.0         # 满减门槛
    target_item_codes: List[str] = field(default_factory=list)
    image_url: str = ""
    is_claimed: bool = True

@dataclass
class OptimizationConstraint:
    """单人多约束背包优化参数"""
    max_budget: float = 999.0                   # 最大预算上限 (元)
    min_items: int = 1                          # 至少包含几件餐品
    required_categories: List[FoodCategory] = field(default_factory=list) # 必须包含的品类
    max_calories: Optional[float] = None        # 最高热量上限 (kcal)
    min_protein: Optional[float] = None         # 最低蛋白质含量 (g)
    max_sodium: Optional[float] = None          # 最高钠含量 (mg)
    preferred_items: List[str] = field(default_factory=list) # 用户明确指定的必点餐品
    excluded_items: List[str] = field(default_factory=list)  # 用户明确忌口不吃的餐品
    prefer_new_arrivals: bool = False           # 优先探索官方新品

@dataclass
class OptimizedPlan:
    """单人运筹优化产出的推荐方案"""
    plan_name: str
    items: List[MenuItem]
    original_total: float
    actual_total: float
    saved_amount: float
    discount_rate: float
    total_nutrition: NutritionInfo
    applied_coupons: List[Coupon] = field(default_factory=list)
    explanation: str = ""
    score: float = 0.0
    reliability: DataReliability = DataReliability.LIVE_VERIFIED

# ================= 多人协同点餐数据结构 =================

@dataclass
class MemberPreference:
    """协同成员个人偏好"""
    name: str
    budget: float = 35.0
    preferred_items: List[str] = field(default_factory=list)
    excluded_items: List[str] = field(default_factory=list)
    is_spicy_ok: bool = True
    prefer_drink: bool = True
    notes: str = ""

@dataclass
class MemberShare:
    """协同成员分摊明细"""
    member_name: str
    individual_items: List[MenuItem]
    individual_original_total: float
    shared_items_cost_share: float
    applied_discount_share: float
    final_payable: float
    saved_amount: float
    nutrition: NutritionInfo = field(default_factory=NutritionInfo)

@dataclass
class GroupOrderPlan:
    """多人/双人协同点餐组合方案"""
    plan_name: str
    members: List[MemberShare]
    shared_items: List[MenuItem]
    total_original: float
    total_actual: float
    total_saved: float
    per_person_avg: float
    reliability: DataReliability = DataReliability.LIVE_VERIFIED
    explanation: str = ""

@dataclass
class StoreInfo:
    """门店信息"""
    store_code: str
    be_code: Optional[str]
    store_name: str
    address: str
    distance: int = 0
    reservation: bool = True
