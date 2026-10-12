"""
数据模型定义模块
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

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

    def __post_init__(self):
        if self.original_price <= 0:
            self.original_price = self.price

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
    """多约束背包优化参数"""
    max_budget: float = 999.0                   # 最大预算上限 (元)
    min_items: int = 1                          # 至少包含几件餐品
    required_categories: List[FoodCategory] = field(default_factory=list) # 必须包含的品类(如必须有主食和饮料)
    max_calories: Optional[float] = None        # 最高热量上限 (kcal)
    min_protein: Optional[float] = None         # 最低蛋白质含量 (g)
    max_sodium: Optional[float] = None          # 最高钠含量 (mg)
    preferred_items: List[str] = field(default_factory=list) # 用户明确指定的必点餐品
    excluded_items: List[str] = field(default_factory=list)  # 用户明确忌口不吃的餐品

@dataclass
class OptimizedPlan:
    """运筹优化产出的推荐方案"""
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

@dataclass
class StoreInfo:
    """门店信息"""
    store_code: str
    be_code: Optional[str]
    store_name: str
    address: str
    distance: int = 0
    reservation: bool = True
