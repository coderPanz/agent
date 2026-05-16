# Agent 天气查询功能实现方案

> 本文档说明如何为 Agent 系统新增「天气查询」工具能力，涵盖工具注册、API 集成、测试方案。

---

## 目录

1. [功能概述](#1-功能概述)
2. [架构设计](#2-架构设计)
3. [实现步骤](#3-实现步骤)
4. [完整代码](#4-完整代码)
5. [测试方案](#5-测试方案)
6. [常见问题](#6-常见问题)

---

## 1. 功能概述

### 需求

当用户询问：
- "北京今天天气如何？"
- "上海明天会下雨吗？"
- "深圳7天天气预报"

Agent 能够自动识别「天气查询」意图，调用天气工具获取实时数据，并返回格式化的答案。

### 实现效果

```
用户: "北京今天天气如何？"
↓
[意图识别] → react
[构建上下文] ✓
[思考推理] 需要查询天气信息
[已调用工具 1 次] → weather_query
Final Answer: 北京今天晴天，气温 15-22°C，风力 3-4 级...
```

---

## 2. 架构设计

### 工具系统工作流

```
┌─────────────────────────────────────────────────────┐
│ 1. builtin.py:                                      │
│    - 使用 @registry.register() 装饰器注册工具       │
│    - 实现异步函数（async def weather_query(...)）   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 2. ReAct Executor:                                  │
│    - 从 registry.get_descriptions() 获取工具列表    │
│    - 注入 REACT_SYSTEM_PROMPT                       │
│    - LLM 识别出需要调用的工具名和参数              │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 3. ToolRegistry.execute():                          │
│    - 查询工具是否存在（防止 hallucination）        │
│    - 执行工具函数（内置超时 + 重试）               │
│    - 返回 ToolResult (success, output, error)      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 4. Observation 反馈:                                │
│    - 将工具结果作为 Observation 追加到对话历史      │
│    - LLM 基于观察结果生成最终答案                   │
└─────────────────────────────────────────────────────┘
```

### 天气数据源选项

| 数据源 | API | 特点 | 推荐度 |
|--------|-----|------|--------|
| **OpenWeather** | openweathermap.org | 免费配额 5000/天，数据准确 | ⭐⭐⭐⭐⭐ |
| **心知天气** | xinzhi.wunderground.com | 国内覆盖良好，中文友好 | ⭐⭐⭐⭐ |
| **和风天气** | qweather.com | 国内官方数据源，需 API Key | ⭐⭐⭐⭐ |
| **MockAPI** | (本地 Stub) | 用于测试，不调用网络 | ⭐ |

**推荐方案**：先用 `MockAPI` 本地测试工具流程，验证后再集成真实 API（OpenWeather 最稳定）。

---

## 3. 实现步骤

### Step 1：配置天气 API

编辑 `backend/.env`，添加天气 API 密钥：

```bash
# 选项 A：OpenWeather（推荐）
WEATHER_API_PROVIDER=openweather
OPENWEATHER_API_KEY=your_api_key_here

# 选项 B：本地 Mock（开发测试）
WEATHER_API_PROVIDER=mock
```

**获取 OpenWeather API Key**：

1. 访问 https://openweathermap.org/api
2. 注册账号 → 创建 Free API Key
3. 复制 API Key 粘贴到 `.env`

**注意**：免费配额约 5000 请求/天，足够开发使用。

---

### Step 2：创建天气服务模块

创建文件：`backend/app/core/agent/tools/weather.py`

```python
import os
import httpx
from datetime import datetime
from typing import Any

class WeatherService:
    """天气查询服务 - 多数据源支持"""
    
    def __init__(self):
        self.provider = os.getenv("WEATHER_API_PROVIDER", "mock")
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "")
    
    async def query(self, city: str, days: int = 1) -> dict[str, Any]:
        """
        查询天气信息
        
        Args:
            city: 城市名称（中文或英文）
            days: 预报天数（1=今天，3=3天预报，7=周天气预报）
        
        Returns:
            {
                "city": "北京",
                "country": "CN",
                "current": {
                    "temp": 15,
                    "feels_like": 13,
                    "description": "晴天",
                    "humidity": 45,
                    "wind_speed": 3.5,
                    "wind_direction": "北风"
                },
                "forecast": [
                    {
                        "date": "2026-05-16",
                        "high": 22,
                        "low": 15,
                        "description": "晴天",
                        "rain_probability": 5
                    }
                ]
            }
        """
        if self.provider == "openweather":
            return await self._query_openweather(city, days)
        elif self.provider == "mock":
            return self._query_mock(city, days)
        else:
            raise ValueError(f"未知的天气数据源: {self.provider}")
    
    async def _query_openweather(self, city: str, days: int) -> dict[str, Any]:
        """调用 OpenWeather API"""
        base_url = "https://api.openweathermap.org/data/2.5"
        
        # 第一步：从城市名获取坐标（地理编码）
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct"
        async with httpx.AsyncClient() as client:
            geo_resp = await client.get(geo_url, params={
                "q": city,
                "appid": self.api_key,
                "limit": 1
            })
            geo_data = geo_resp.json()
            
            if not geo_data:
                return {"error": f"未找到城市: {city}"}
            
            lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
            city_name = geo_data[0].get("name", city)
            country = geo_data[0].get("country", "")
            
            # 第二步：调用 weather API 获取天气数据
            weather_url = f"{base_url}/weather"
            weather_resp = await client.get(weather_url, params={
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",  # 摄氏度
                "lang": "zh_cn"    # 中文
            })
            current = weather_resp.json()
            
            # 第三步：获取 5 天预报（如需更长需付费）
            forecast_url = f"{base_url}/forecast"
            forecast_resp = await client.get(forecast_url, params={
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "lang": "zh_cn",
                "cnt": min(days * 8, 40)  # 最多 5 天（5*8=40）
            })
            forecast_data = forecast_resp.json()
        
        # 格式化当前天气
        weather = current.get("weather", [{}])[0]
        main = current.get("main", {})
        wind = current.get("wind", {})
        
        result = {
            "city": city_name,
            "country": country,
            "current": {
                "temp": round(main.get("temp", 0), 1),
                "feels_like": round(main.get("feels_like", 0), 1),
                "description": weather.get("main", ""),
                "detail": weather.get("description", ""),
                "humidity": main.get("humidity", 0),
                "pressure": main.get("pressure", 0),
                "wind_speed": round(wind.get("speed", 0), 1),
                "wind_direction": self._get_wind_direction(wind.get("deg", 0)),
            }
        }
        
        # 格式化预报数据
        forecast = []
        seen_dates = set()
        
        for item in forecast_data.get("list", []):
            dt = datetime.fromtimestamp(item["dt"])
            date_str = dt.strftime("%Y-%m-%d")
            
            # 去重：每天只保留一条预报（取中午的数据）
            if date_str in seen_dates or len(forecast) >= days:
                continue
            
            weather_item = item.get("weather", [{}])[0]
            main_item = item.get("main", {})
            
            forecast.append({
                "date": date_str,
                "temp": round(main_item.get("temp", 0), 1),
                "temp_max": round(main_item.get("temp_max", 0), 1),
                "temp_min": round(main_item.get("temp_min", 0), 1),
                "description": weather_item.get("main", ""),
                "detail": weather_item.get("description", ""),
                "humidity": main_item.get("humidity", 0),
                "rain_probability": round(item.get("pop", 0) * 100, 0),
            })
            seen_dates.add(date_str)
        
        result["forecast"] = forecast
        return result
    
    def _query_mock(self, city: str, days: int) -> dict[str, Any]:
        """本地 Mock 数据（用于开发测试）"""
        mock_data = {
            "北京": {
                "city": "北京",
                "country": "CN",
                "current": {
                    "temp": 15.2,
                    "feels_like": 13.8,
                    "description": "晴天",
                    "detail": "晴朗天气",
                    "humidity": 45,
                    "pressure": 1013,
                    "wind_speed": 3.5,
                    "wind_direction": "北风"
                },
                "forecast": [
                    {
                        "date": "2026-05-16",
                        "temp": 18.5,
                        "temp_max": 22.0,
                        "temp_min": 15.0,
                        "description": "晴天",
                        "detail": "晴朗天气",
                        "humidity": 45,
                        "rain_probability": 5
                    },
                    {
                        "date": "2026-05-17",
                        "temp": 16.0,
                        "temp_max": 20.0,
                        "temp_min": 14.0,
                        "description": "多云",
                        "detail": "多云天气",
                        "humidity": 55,
                        "rain_probability": 10
                    },
                    {
                        "date": "2026-05-18",
                        "temp": 14.5,
                        "temp_max": 19.0,
                        "temp_min": 12.0,
                        "description": "小雨",
                        "detail": "小雨天气",
                        "humidity": 65,
                        "rain_probability": 60
                    }
                ]
            },
            "上海": {
                "city": "上海",
                "country": "CN",
                "current": {
                    "temp": 18.5,
                    "feels_like": 17.2,
                    "description": "多云",
                    "detail": "多云天气",
                    "humidity": 55,
                    "pressure": 1012,
                    "wind_speed": 2.8,
                    "wind_direction": "东风"
                },
                "forecast": [
                    {
                        "date": "2026-05-16",
                        "temp": 20.0,
                        "temp_max": 24.0,
                        "temp_min": 17.0,
                        "description": "多云",
                        "detail": "多云天气",
                        "humidity": 55,
                        "rain_probability": 15
                    }
                ]
            }
        }
        
        # 默认返回 "北京" 数据
        city_data = mock_data.get(city, mock_data["北京"])
        
        # 截取指定天数的预报
        result = {
            "city": city_data["city"],
            "country": city_data["country"],
            "current": city_data["current"],
            "forecast": city_data["forecast"][:days]
        }
        
        return result
    
    def _get_wind_direction(self, degrees: float) -> str:
        """将风向角度转换为方向名称"""
        directions = [
            "北风", "北偏东风", "东北风", "东偏北风",
            "东风", "东偏南风", "东南风", "南偏东风",
            "南风", "南偏西风", "西南风", "西偏南风",
            "西风", "西偏北风", "西北风", "北偏西风"
        ]
        index = round((degrees + 11.25) / 22.5) % 16
        return directions[index]
```

---

### Step 3：在 builtin.py 中注册工具

编辑 `backend/app/core/agent/tools/builtin.py`，添加天气查询工具：

```python
from app.core.agent.tools.registry import ToolRegistry
from app.core.agent.tools.weather import WeatherService

registry = ToolRegistry.get_instance()
weather_service = WeatherService()

# ── 原有工具 ──────────────────────────────────────────
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
            return f"查询失败: {result['error']}"
        
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
```

---

## 4. 完整代码

### 文件结构总览

```
backend/
├── app/
│   ├── core/agent/
│   │   ├── tools/
│   │   │   ├── builtin.py          ← 修改：添加 weather_query 注册
│   │   │   ├── registry.py         （无需修改）
│   │   │   ├── schema.py           （无需修改）
│   │   │   └── weather.py          ← 新建：天气服务模块
│   │   ├── executors/react/
│   │   │   └── executor.py         （无需修改）
│   │   └── ...
│   └── ...
├── .env                             ← 修改：添加 WEATHER_API_PROVIDER
└── ...
```

### 关键修改点

**1. builtin.py** - 添加天气工具注册（见上方 Step 3）

**2. weather.py** - 完整的天气服务实现（见上方 Step 2）

**3. .env** - 配置天气数据源

```bash
# 开发环境推荐：使用 Mock 数据
WEATHER_API_PROVIDER=mock

# 生产环境：使用 OpenWeather API
WEATHER_API_PROVIDER=openweather
OPENWEATHER_API_KEY=sk_xxxx_xxxx_xxxx
```

---

## 5. 测试方案

### 5.1 单元测试：天气服务

创建 `backend/tests/test_weather_service.py`：

```python
import pytest
import asyncio
from app.core.agent.tools.weather import WeatherService

@pytest.fixture
def weather_service_mock():
    """创建本地 Mock 天气服务"""
    import os
    os.environ["WEATHER_API_PROVIDER"] = "mock"
    return WeatherService()

@pytest.mark.asyncio
async def test_query_mock_beijing(weather_service_mock):
    """测试 Mock 数据 - 北京"""
    result = await weather_service_mock.query("北京", days=1)
    
    assert result["city"] == "北京"
    assert "current" in result
    assert "forecast" in result
    assert len(result["forecast"]) == 1
    assert result["current"]["temp"] > 0

@pytest.mark.asyncio
async def test_query_mock_shanghai_3days(weather_service_mock):
    """测试 Mock 数据 - 上海 3 天预报"""
    result = await weather_service_mock.query("上海", days=3)
    
    assert result["city"] == "上海"
    assert len(result["forecast"]) == 1  # Mock 上海只有 1 天
    
@pytest.mark.asyncio
async def test_wind_direction_conversion(weather_service_mock):
    """测试风向转换"""
    assert weather_service_mock._get_wind_direction(0) == "北风"
    assert weather_service_mock._get_wind_direction(90) == "东风"
    assert weather_service_mock._get_wind_direction(180) == "南风"
    assert weather_service_mock._get_wind_direction(270) == "西风"
```

运行测试：

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/test_weather_service.py -v
```

### 5.2 工具集成测试

创建 `backend/tests/test_weather_tool_integration.py`：

```python
import pytest
from app.core.agent.tools.registry import ToolRegistry
from app.core.agent.tools.builtin import weather_query

@pytest.mark.asyncio
async def test_weather_tool_registered():
    """验证工具是否正确注册"""
    registry = ToolRegistry.get_instance()
    assert registry.has_tool("weather_query")
    
    # 检查工具描述是否包含在注册表中
    descriptions = registry.get_descriptions()
    assert "weather_query" in descriptions

@pytest.mark.asyncio
async def test_weather_tool_execution():
    """测试工具执行"""
    registry = ToolRegistry.get_instance()
    
    result = await registry.execute(
        "weather_query",
        {"city": "北京", "days": 1}
    )
    
    assert result.success == True
    assert "当前天气" in result.output or "北京" in result.output
    assert result.tool_name == "weather_query"

@pytest.mark.asyncio
async def test_weather_tool_error_handling():
    """测试工具错误处理"""
    registry = ToolRegistry.get_instance()
    
    # 测试参数错误
    result = await registry.execute(
        "weather_query",
        {"city": ""}  # 空城市名
    )
    
    # 工具应该返回错误，但不会崩溃
    assert isinstance(result.output, str)
```

### 5.3 端到端测试：前端

**问题 1：简单天气查询**

```
用户输入: "北京今天天气怎么样？"
预期流程:
  [意图识别] react
  [构建上下文] ✓
  [思考推理] 需要查询北京天气
  [已调用工具 1 次] → weather_query
  [质量检验] ✓
  [最终回答] 包含温度、描述、风力等信息
```

**问题 2：多天预报**

```
用户输入: "上海一周天气预报"
预期流程:
  [已调用工具 1 次] → weather_query(days=7)
  [最终回答] 包含 7 天预报，每天的温度、天气、降水概率
```

**问题 3：错误处理**

```
用户输入: "火星天气"
预期流程:
  [已调用工具 1 次] → weather_query
  [最终回答] "抱歉，火星不是地球上的城市..."
```

### 5.4 API 调试

使用 curl 直接测试 SSE 端点：

```bash
# 测试天气查询意图
curl -X POST 'http://localhost:8000/api/agent/stream' \
  -H 'Content-Type: application/json' \
  -d '{"query":"北京明天天气如何","session_id":null}'

# 观察事件序列
# 应该看到：
# - start
# - node_done: router (react)
# - node_done: context_builder
# - tool_call: {tools: {weather_query: 1}}
# - node_done: react_executor
# - node_done: critic
# - answer: 包含天气信息
# - done
```

---

## 6. 常见问题

### Q1：如何切换天气数据源？

**A：** 修改 `.env` 文件：

```bash
# 开发使用 Mock
WEATHER_API_PROVIDER=mock

# 生产使用 OpenWeather
WEATHER_API_PROVIDER=openweather
OPENWEATHER_API_KEY=your_key
```

重启后端服务即可生效。

---

### Q2：OpenWeather API 免费配额是多少？

**A：** 免费计划限制：
- **API 调用数**：5,000 请求/天
- **数据保留期**：120 天历史数据
- **更新频率**：10-15 分钟更新一次

足够个人使用和开发测试。超过需要升级付费计划。

---

### Q3：如何处理 API 超时？

**A：** 工具已内置超时控制：

```python
@registry.register(
  name="weather_query",
  timeout=10.0,      # 10 秒超时
  max_retry=2,       # 最多重试 2 次
)
```

如果 10 秒内未收到响应，自动重试。重试 2 次仍失败则返回错误。

---

### Q4：支持哪些城市名？

**A：** 支持：
- **中文城市名**：北京、上海、深圳、杭州、西安、...
- **英文城市名**：Beijing、Shanghai、Shenzhen、...
- **缩写**：NYC（纽约）、LA（洛杉矶）、...

OpenWeather API 会自动地理编码解析城市名为坐标。

---

### Q5：预报天数有限制吗？

**A：** 
- **Mock 数据**：北京 3 天、上海 1 天（硬编码）
- **OpenWeather 免费**：最多 5 天（需要调用 `/forecast5` 端点）
- **OpenWeather 付费**：可支持 16 天预报

代码会自动截取请求天数以内的预报数据。

---

### Q6：能同时查询多个城市吗？

**A：** 当前工具设计只支持单个城市。若需多城市查询，可：

1. **方案 A**：用户连续询问，Agent 分别调用
   ```
   用户："北京明天天气？"
   Agent：查询北京
   用户："那上海呢？"
   Agent：查询上海
   ```

2. **方案 B**：扩展工具支持数组参数
   ```python
   @registry.register(name="weather_compare", ...)
   async def weather_compare(cities: list[str], days: int = 1):
       # 并发查询多个城市
       tasks = [weather_service.query(city, days) for city in cities]
       return await asyncio.gather(*tasks)
   ```

---

### Q7：如何记录工具调用日志？

**A：** 使用 Tracer 系统（已集成到 ReAct Executor）：

```python
# app/core/agent/observability/trace.py
tracer = Tracer(session_id=state.session_id)

# 自动记录
await tracer.log_step_start(step)
tool_result = await registry.execute(tool_name, tool_input)
await tracer.log_tool_call(tool_name, tool_input, tool_result.output)
```

所有工具调用会自动记录到 `trace.log`。

---

## 总结

通过本实现方案：

✅ **新增了天气查询工具**
- 支持实时天气 + 多天预报
- 支持多数据源（Mock、OpenWeather）
- 内置超时 + 重试机制

✅ **工具自动集成到 ReAct 循环**
- LLM 自动识别天气查询意图
- 工具描述自动注入 Prompt
- 工具结果自动反馈作为 Observation

✅ **完整测试覆盖**
- 单元测试：天气服务
- 集成测试：工具注册 + 执行
- 端到端测试：SSE 事件流

继续扩展时，可按相同模式增加：日历、翻译、新闻、股票等工具。

