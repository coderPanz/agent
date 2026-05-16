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
    return "【工具未接入】web_search 暂未实现，请使用已有工具完成任务。"


@registry.register(
  name="calculator",
  description="数学计算。参数: {\"expression\": \"数学表达式，如 '2 + 3 * 4'\"}",
  timeout=5.0,
  max_retry=1,
)
async def calculator(expression: str) -> str:
    return "【工具未接入】calculator 暂未实现，请使用已有工具完成任务。"



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
        days = min(max(days, 1), 4)  # 高德最多支持 4 天预报

        result = await weather_service.query(city, days)

        if "error" in result:
            return f"查询失败：{result['error']}"

        province = result.get("province", "")
        city_label = result.get("city", city)
        output = f"【{province}{city_label} 天气信息】\n\n"

        current = result.get("current", {})
        output += "当前天气:\n"
        output += f"  温度: {current.get('temp', 'N/A')}°C\n"
        output += f"  天气: {current.get('description', 'N/A')}\n"
        output += f"  湿度: {current.get('humidity', 'N/A')}%\n"
        output += f"  风向风力: {current.get('wind_direction', 'N/A')} {current.get('wind_speed', 'N/A')} 级\n"
        output += f"  发布时间: {current.get('report_time', 'N/A')}\n\n"

        forecast = result.get("forecast", [])
        if forecast:
            output += f"{days}天预报:\n"
            for item in forecast:
                output += (
                    f"  {item.get('date', 'N/A')} (周{item.get('week', '?')}): "
                    f"白天{item.get('description', 'N/A')} / 夜间{item.get('night_description', 'N/A')}  "
                    f"{item.get('temp_min', 'N/A')}-{item.get('temp_max', 'N/A')}°C  "
                    f"{item.get('wind_direction', 'N/A')}{item.get('wind_power', 'N/A')}级\n"
                )

        return output
    
    except Exception as e:
        return f"天气查询异常: {str(e)}"