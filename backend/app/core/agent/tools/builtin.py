from app.core.agent.tools.registry import ToolRegistry
from app.core.agent.tools.models import WeatherService

registry = ToolRegistry.get_instance()
weather_service = WeatherService()


# ── 定义注册内置工具 ──────────────────────────────────────
# 在定义工具函数的同时，把这个函数自动注册到工具注册表里。
@registry.register(
  name="web_search",
  description="搜索互联网信息。参数: {\"query\": \"搜索关键词\"}",
  timeout=15.0,
  max_retry=1,
)
async def web_search(query: str) -> str:
    pass


@registry.register(
  name="calculator",
  description="数学计算。参数: {\"expression\": \"数学表达式，如 '2 + 3 * 4'\"}",
  timeout=5.0,
  max_retry=1,
)
async def calculator(expression: str) -> str:
    pass



# ── 新增：天气查询工具 ────────────────────────────────
@registry.register(
  name="weather_query",
  description="查询城市天气信息。参数: {\"city\": \"城市名\", \"days\": 1|3|7}。示例: {\"city\": \"北京\", \"days\": 3}",
  timeout=10.0,
  max_retry=2,
)
async def weather_query(city: str, days: int = 1) -> str:
    """
    查询天气信息
    
    Args:
        city: 城市名（支持中文或英文）
        days: 预报天数，可选 1/3/7 天（默认 1 天）
    
    Returns:
        格式化的天气信息文本
    """
    try:
        # 验证天数参数
        if days not in (1, 3, 7):
            days = min(7, max(1, days))

        # 调用天气服务
        result = await weather_service.query(city, days)
        
        # 检查错误
        if "error" in result:
            return f"查询失败， {result['error']}"


        # 格式化输出
        output = f"【{result['city']} {result.get('country', '')} 天气信息】\n\n"
        
        # 当前天气
        current = result.get("current", {})
        output += f"🌡️ 当前天气:\n"
        output += f"  温度: {current.get('temp', 'N/A')}°C (体感 {current.get('feels_like', 'N/A')}°C)\n"
        output += f"  天气: {current.get('description', 'N/A')} - {current.get('detail', '')}\n"
        output += f"  湿度: {current.get('humidity', 'N/A')}%\n"
        output += f"  风力: {current.get('wind_direction', 'N/A')} {current.get('wind_speed', 'N/A')} m/s\n\n"
        
        # 未来预报
        forecast = result.get("forecast", [])
        if forecast:
            output += f"📅 {days}天预报:\n"
            for item in forecast:
                output += f"  {item.get('date', 'N/A')}: "
                output += f"{item.get('description', 'N/A')} "
                output += f"{item.get('temp_min', 'N/A')}-{item.get('temp_max', 'N/A')}°C "
                output += f"降水概率 {item.get('rain_probability', 'N/A')}%\n"
        
        return output
    
    except Exception as e:
        return f"天气查询异常: {str(e)}"