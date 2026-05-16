import os
import httpx
from typing import Any


class WeatherService:
    """天气查询服务 - 高德 Web 服务 API"""

    BASE_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

    def __init__(self):
        self.api_key = os.getenv("GAODE_API_KEY", "")

    async def query(self, city: str, days: int = 1) -> dict[str, Any]:
        """
        查询天气信息

        Args:
            city: 城市名称或 adcode（如"北京"或"110000"）
            days: 预报天数（1-4，高德最多支持4天）

        Returns:
            {
                "city": "北京市",
                "province": "北京",
                "current": {
                    "temp": 22.0,
                    "description": "晴",
                    "humidity": 30,
                    "wind_direction": "北风",
                    "wind_speed": "≤3",
                    "report_time": "2026-05-16 12:00:00"
                },
                "forecast": [
                    {
                        "date": "2026-05-16",
                        "week": "6",
                        "temp_max": 25.0,
                        "temp_min": 17.0,
                        "description": "晴",
                        "night_description": "晴",
                        "wind_direction": "北风",
                        "wind_power": "≤3"
                    }
                ]
            }
        """
        async with httpx.AsyncClient() as client:
            live_resp = await client.get(self.BASE_URL, params={
                "city": city,
                "key": self.api_key,
                "extensions": "base",
                "output": "JSON",
            })
            live_data = live_resp.json()

            if live_data.get("status") != "1" or not live_data.get("lives"):
                return {"error": f"查询失败：{live_data.get('info', '未知错误')}，城市：{city}"}

            forecast_resp = await client.get(self.BASE_URL, params={
                "city": city,
                "key": self.api_key,
                "extensions": "all",
                "output": "JSON",
            })
            forecast_data = forecast_resp.json()

        live = live_data["lives"][0]
        result: dict[str, Any] = {
            "city": live.get("city", city),
            "province": live.get("province", ""),
            "current": {
                "temp": float(live.get("temperature", 0)),
                "description": live.get("weather", ""),
                "humidity": int(live.get("humidity", 0)),
                "wind_direction": live.get("winddirection", "") + "风",
                "wind_speed": live.get("windpower", ""),
                "report_time": live.get("reporttime", ""),
            },
        }

        forecast = []
        if forecast_data.get("status") == "1" and forecast_data.get("forecasts"):
            casts = forecast_data["forecasts"][0].get("casts", [])
            for cast in casts[:max(days, 4)]:
                forecast.append({
                    "date": cast.get("date", ""),
                    "week": cast.get("week", ""),
                    "temp_max": float(cast.get("daytemp", 0)),
                    "temp_min": float(cast.get("nighttemp", 0)),
                    "description": cast.get("dayweather", ""),
                    "night_description": cast.get("nightweather", ""),
                    "wind_direction": cast.get("daywind", "") + "风",
                    "wind_power": cast.get("daypower", ""),
                })

        result["forecast"] = forecast
        return result
