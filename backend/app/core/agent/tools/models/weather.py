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
