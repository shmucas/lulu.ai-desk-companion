import httpx


class WeatherTool:
    name = "weather"
    description = "Get current weather and today's high/low for a city"
    parameter_spec = {"location": {"type": "string", "description": "City name, e.g. Atlanta, GA"}}

    def execute(self, location: str = "Atlanta, GA") -> str:
        try:
            with httpx.Client(timeout=10) as client:
                geo = client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": location, "count": 1},
                ).json()

                if not geo.get("results"):
                    return f"Could not find location: {location}."

                r = geo["results"][0]
                lat, lon = r["latitude"], r["longitude"]
                name = f"{r.get('name', location)}, {r.get('country', '')}"

                weather = client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                        "daily": "temperature_2m_max,temperature_2m_min",
                        "temperature_unit": "fahrenheit",
                        "wind_speed_unit": "mph",
                        "forecast_days": 1,
                        "timezone": "auto",
                    },
                ).json()

                c = weather.get("current", {})
                d = weather.get("daily", {})
                condition = _weather_code(c.get("weather_code", 0))

                return (
                    f"Current weather in {name}: {condition}, {c.get('temperature_2m')}°F. "
                    f"Humidity {c.get('relative_humidity_2m')}%, wind {c.get('wind_speed_10m')} mph. "
                    f"Today's high {d.get('temperature_2m_max', [None])[0]}°F, "
                    f"low {d.get('temperature_2m_min', [None])[0]}°F."
                )
        except Exception as e:
            return f"Could not fetch weather: {e}"


def _weather_code(code: int) -> str:
    if code == 0: return "Clear sky"
    if code in (1, 2, 3): return ["Mainly clear", "Partly cloudy", "Overcast"][code - 1]
    if code in (45, 48): return "Foggy"
    if code in (51, 53, 55): return "Drizzle"
    if code in (61, 63, 65): return "Rain"
    if code in (71, 73, 75): return "Snow"
    if code in (80, 81, 82): return "Rain showers"
    if code in (95, 96, 99): return "Thunderstorm"
    return "Mixed conditions"
