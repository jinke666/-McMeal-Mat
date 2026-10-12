"""
配置管理模块
"""

import os
from dataclasses import dataclass

@dataclass
class Config:
    """系统配置参数"""
    mcp_url: str = os.getenv("MCD_MCP_URL", "https://mcp.mcd.cn")
    mcp_token: str = os.getenv("MCD_MCP_TOKEN", "")
    timeout: float = float(os.getenv("MCD_MCP_TIMEOUT", "15.0"))
    default_city: str = os.getenv("MCD_DEFAULT_CITY", "上海")
    default_store_keyword: str = os.getenv("MCD_DEFAULT_KEYWORD", "人民广场")
    
    # 算法求解参数
    max_search_depth: int = int(os.getenv("MCMEAL_SEARCH_DEPTH", "5000"))
    calorie_tolerance_ratio: float = 0.15

config = Config()
