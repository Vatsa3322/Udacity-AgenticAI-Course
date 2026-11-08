import os
import json
import math
import random
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # older langchain
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from models.energy import DatabaseManager
 
# Initialize database manager
db_manager = DatabaseManager()
 
# ===== MODULE-LEVEL HELPERS / CONSTANTS - the tools below depend on these; copy them too =====
BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "data" / "documents"
PERSIST_DIR = BASE_DIR / "data" / "vectorstore"
BASE_PRICE_PER_KWH = 0.12
SOLAR_PEAK_IRRADIANCE = 900  # W/m2 on a clear day
 
 
def _parse_date(date_str):
    if not date_str or str(date_str).lower() == "today":
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if str(date_str).lower() == "tomorrow":
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return datetime.strptime(date_str, "%Y-%m-%d")
 
 
# ===== end of module-level helpers =====
 
 
# ---------------------------------------------------------------- weather (mocked)
@tool
def get_weather_forecast(location: str = "San Francisco, CA", days: int = 3) -> Dict[str, Any]:
    """
    Get weather forecast for a specific location and number of days.
 
    Args:
        location (str): Location to get weather for (e.g., "San Francisco, CA")
        days (int): Number of days to forecast (1-7)
 
    Returns:
        Dict[str, Any]: Weather forecast data including temperature, conditions, and solar irradiance
    """
    try:
        days = max(1, min(int(days), 7))
        cloud_factor = {"sunny": 1.0, "partly_cloudy": 0.65, "cloudy": 0.3}
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
 
        hourly, daily = [], []
        for d in range(days):
            day = today + timedelta(days=d)
            rnd = random.Random(f"{location}-{day:%Y-%m-%d}")  # deterministic per place/date
            cond = rnd.choice(["sunny", "sunny", "partly_cloudy", "cloudy"])
            t_mean, humidity = rnd.uniform(16, 28), rnd.randint(35, 80)
            wind = round(rnd.uniform(3, 25), 1)
            solar_total = 0.0
            temps = []
            for hour in range(24):
                temp = round(t_mean + 6 * math.sin(3.1416 * (hour - 8) / 12) + rnd.uniform(-1, 1), 1)
                sun = max(0.0, math.sin(3.1416 * (hour - 6) / 13)) if 6 <= hour <= 19 else 0.0
                irr = round(SOLAR_PEAK_IRRADIANCE * sun * cloud_factor[cond] * rnd.uniform(0.9, 1.05), 1)
                solar_total += irr
                temps.append(temp)
                if d < 2 or hour % 3 == 0:   # full detail for the next 2 days, 3-hourly after that
                    hourly.append({"date": f"{day:%Y-%m-%d}", "hour": hour, "temperature_c": temp,
                                   "condition": cond, "solar_irradiance": irr,
                                   "humidity": humidity, "wind_speed": wind})
            daily.append({"date": f"{day:%Y-%m-%d}", "weekday": day.strftime("%A"),
                          "condition": cond, "high_c": max(temps), "low_c": min(temps),
                          # 5 kW array, ~ (sum of hourly irradiance / 1000) * 5 kW * 0.8 efficiency
                          "expected_solar_kwh": round(solar_total / 1000 * 5 * 0.8, 1),
                          "best_solar_hours": "10:00-15:00" if cond != "cloudy" else "11:00-14:00 (weak)"})
 
        cur = hourly[min(datetime.now().hour, len(hourly) - 1)]
        return {
            "location": location,
            "forecast_days": days,
            "current": {"temperature_c": cur["temperature_c"], "condition": cur["condition"],
                        "humidity": cur["humidity"], "wind_speed": cur["wind_speed"]},
            "daily_summary": daily,
            "hourly": hourly,
        }
    except Exception as e:
        return {"error": f"Failed to get weather forecast: {str(e)}"}
 
 
# ---------------------------------------------------------------- prices (mocked)
@tool
def get_electricity_prices(date: str = None) -> Dict[str, Any]:
    """
    Get electricity prices for a specific date or current day.
 
    Args:
        date (str): Date in YYYY-MM-DD format (defaults to today; 'tomorrow' also accepted)
 
    Returns:
        Dict[str, Any]: Electricity pricing data with hourly rates
    """
    try:
        d = _parse_date(date)
        weekday = d.weekday()
        hourly_rates = []
        for hour in range(24):
            if 16 <= hour < 21:
                period, mult, demand = "peak", 2.8, 0.08
            elif 6 <= hour < 22:
                period, mult, demand = "mid_peak", 1.6, 0.02
            else:
                period, mult, demand = "off_peak", 1.0, 0.0  # no demand charge off-peak
            # Wednesday demand-response event: prices spike 16:00-20:00
            if weekday == 2 and 16 <= hour < 20:
                period, mult, demand = "peak_spike", 4.0, 0.15
            hourly_rates.append({"hour": hour, "rate": round(BASE_PRICE_PER_KWH * mult, 3),
                                 "period": period, "demand_charge": demand})
        rates = [h["rate"] for h in hourly_rates]
        return {
            "date": f"{d:%Y-%m-%d}", "weekday": d.strftime("%A"),
            "pricing_type": "time_of_use", "currency": "USD", "unit": "per_kWh",
            "hourly_rates": hourly_rates,
            "summary": {
                "cheapest_hours": [h["hour"] for h in hourly_rates if h["rate"] == min(rates)],
                "most_expensive_hours": [h["hour"] for h in hourly_rates if h["rate"] == max(rates)],
                "min_rate": min(rates), "max_rate": max(rates),
                "price_spike": weekday == 2,
            },
        }
    except Exception as e:
        return {"error": f"Failed to get electricity prices: {str(e)}"}
 
 
@tool
def query_energy_usage(start_date: str, end_date: str, device_type: str = None) -> Dict[str, Any]:
    """
    Query energy usage data from the database for a specific date range.
 
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        device_type (str): Optional device type filter (e.g., "EV", "HVAC", "appliance")
 
    Returns:
        Dict[str, Any]: Energy usage data with consumption details
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
 
        records = db_manager.get_usage_by_date_range(start_dt, end_dt)
 
        if device_type:
            records = [r for r in records if (r.device_type or "").lower() == device_type.lower()]
 
        # Per-device summary keeps the response small and easy for the LLM to use
        by_device, by_hour = {}, {}
        for r in records:
            by_hour[r.timestamp.hour] = by_hour.get(r.timestamp.hour, 0) + r.consumption_kwh
            k = r.device_name or r.device_type
            e = by_device.setdefault(k, {"device_type": r.device_type, "kwh": 0.0, "cost_usd": 0.0})
            e["kwh"] += r.consumption_kwh
            e["cost_usd"] += r.cost_usd or 0
        for e in by_device.values():
            e["kwh"], e["cost_usd"] = round(e["kwh"], 2), round(e["cost_usd"], 2)
 
        usage_data = {
            "start_date": start_date,
            "end_date": end_date,
            "device_type": device_type,
            "total_records": len(records),
            "total_consumption_kwh": round(sum(r.consumption_kwh for r in records), 2),
            "total_cost_usd": round(sum(r.cost_usd or 0 for r in records), 2),
            "by_device": dict(sorted(by_device.items(), key=lambda x: -x[1]["kwh"])),
            "peak_usage_hours": [h for h, _ in sorted(by_hour.items(), key=lambda x: -x[1])[:3]],
            "records": []
        }
 
        for record in records[:48]:  # cap raw rows to protect the LLM context window
            usage_data["records"].append({
                "timestamp": record.timestamp.isoformat(),
                "consumption_kwh": record.consumption_kwh,
                "device_type": record.device_type,
                "device_name": record.device_name,
                "cost_usd": record.cost_usd
            })
        if len(records) > 48:
            usage_data["note"] = f"Showing first 48 of {len(records)} records; totals and by_device cover ALL records."
 
        return usage_data
    except Exception as e:
        return {"error": f"Failed to query energy usage: {str(e)}"}
 
 
@tool
def query_solar_generation(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Query solar generation data from the database for a specific date range.
 
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
 
    Returns:
        Dict[str, Any]: Solar generation data with production details
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
 
        records = db_manager.get_generation_by_date_range(start_dt, end_dt)
 
        generation_data = {
            "start_date": start_date,
            "end_date": end_date,
            "total_records": len(records),
            "total_generation_kwh": round(sum(r.generation_kwh for r in records), 2),
            "average_daily_generation": round(sum(r.generation_kwh for r in records) / max(1, (end_dt - start_dt).days), 2),
            "records": []
        }
 
        for record in records[:48]:
            generation_data["records"].append({
                "timestamp": record.timestamp.isoformat(),
                "generation_kwh": record.generation_kwh,
                "weather_condition": record.weather_condition,
                "temperature_c": record.temperature_c,
                "solar_irradiance": record.solar_irradiance
            })
 
        return generation_data
    except Exception as e:
        return {"error": f"Failed to query solar generation: {str(e)}"}
 
 
@tool
def get_recent_energy_summary(hours: int = 24) -> Dict[str, Any]:
    """
    Get a summary of recent energy usage and solar generation.
 
    Args:
        hours (int): Number of hours to look back (default 24)
 
    Returns:
        Dict[str, Any]: Summary of recent energy data
    """
    try:
        usage_records = db_manager.get_recent_usage(hours)
        generation_records = db_manager.get_recent_generation(hours)
 
        summary = {
            "time_period_hours": hours,
            "usage": {
                "total_consumption_kwh": round(sum(r.consumption_kwh for r in usage_records), 2),
                "total_cost_usd": round(sum(r.cost_usd or 0 for r in usage_records), 2),
                "device_breakdown": {}
            },
            "generation": {
                "total_generation_kwh": round(sum(r.generation_kwh for r in generation_records), 2),
                "average_weather": "sunny" if generation_records else "unknown"
            }
        }
 
        # Calculate device breakdown
        for record in usage_records:
            device = record.device_type or "unknown"
            if device not in summary["usage"]["device_breakdown"]:
                summary["usage"]["device_breakdown"][device] = {
                    "consumption_kwh": 0,
                    "cost_usd": 0,
                    "records": 0
                }
            summary["usage"]["device_breakdown"][device]["consumption_kwh"] += record.consumption_kwh
            summary["usage"]["device_breakdown"][device]["cost_usd"] += record.cost_usd or 0
            summary["usage"]["device_breakdown"][device]["records"] += 1
 
        # Round the breakdown values
        for device_data in summary["usage"]["device_breakdown"].values():
            device_data["consumption_kwh"] = round(device_data["consumption_kwh"], 2)
            device_data["cost_usd"] = round(device_data["cost_usd"], 2)
 
        return summary
    except Exception as e:
        return {"error": f"Failed to get recent energy summary: {str(e)}"}
 
 
# ---------------------------------------------------------------- RAG
def _embeddings():
    return OpenAIEmbeddings(
        base_url="https://openai.vocareum.com/v1",
        api_key="voc-97413346816909255557026adb404c225bc0.17835215",
    )
 
 
def get_vectorstore(force_rebuild: bool = False):
    """Create the vector store from ALL .txt files in data/documents if it doesn't exist,
    otherwise load the existing one. Use force_rebuild=True after adding documents."""
    if force_rebuild and PERSIST_DIR.exists():
        shutil.rmtree(PERSIST_DIR)
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
 
    if not (PERSIST_DIR / "chroma.sqlite3").exists():
        documents = []
        for doc_path in sorted(DOCS_DIR.glob("*.txt")):   # every document, not a hardcoded pair
            documents.extend(TextLoader(str(doc_path), encoding="utf-8").load())
        splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(documents)
        return Chroma.from_documents(documents=splits, embedding=_embeddings(),
                                     persist_directory=str(PERSIST_DIR))
    return Chroma(persist_directory=str(PERSIST_DIR), embedding_function=_embeddings())
 
 
@tool
def search_energy_tips(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search for energy-saving tips and best practices using RAG.
 
    Args:
        query (str): Search query for energy tips
        max_results (int): Maximum number of results to return
 
    Returns:
        Dict[str, Any]: Relevant energy tips and best practices
    """
    try:
        vectorstore = get_vectorstore()
        docs = vectorstore.similarity_search(query, k=max_results)
 
        results = {
            "query": query,
            "total_results": len(docs),
            "tips": []
        }
 
        for i, doc in enumerate(docs):
            results["tips"].append({
                "rank": i + 1,
                "content": doc.page_content,
                "source": Path(doc.metadata.get("source", "unknown")).name,
                "relevance_score": "high" if i < 2 else "medium" if i < 4 else "low"
            })
 
        return results
    except Exception as e:
        return {"error": f"Failed to search energy tips: {str(e)}"}
 
 
@tool
def calculate_energy_savings(device_type: str, current_usage_kwh: float,
                             optimized_usage_kwh: float, price_per_kwh: float = 0.12,
                             optimized_price_per_kwh: float = None) -> Dict[str, Any]:
    """
    Calculate potential energy savings from optimization.
 
    Use optimized_usage_kwh < current_usage_kwh for efficiency savings. To model SHIFTING a load
    to a cheaper time (same kWh, lower rate), pass the same kWh for both and set
    optimized_price_per_kwh to the cheaper rate.
 
    Args:
        device_type (str): Type of device being optimized
        current_usage_kwh (float): Current energy usage in kWh
        optimized_usage_kwh (float): Optimized energy usage in kWh
        price_per_kwh (float): Current price per kWh (default 0.12)
        optimized_price_per_kwh (float): Price per kWh after optimization (defaults to price_per_kwh)
 
    Returns:
        Dict[str, Any]: Savings calculation results
    """
    new_price = price_per_kwh if optimized_price_per_kwh is None else optimized_price_per_kwh
    current_cost = current_usage_kwh * price_per_kwh
    optimized_cost = optimized_usage_kwh * new_price
    savings_kwh = current_usage_kwh - optimized_usage_kwh
    savings_usd = current_cost - optimized_cost
    savings_percentage = (savings_usd / current_cost) * 100 if current_cost > 0 else 0
 
    return {
        "device_type": device_type,
        "current_usage_kwh": current_usage_kwh,
        "optimized_usage_kwh": optimized_usage_kwh,
        "savings_kwh": round(savings_kwh, 2),
        "current_cost_usd": round(current_cost, 2),
        "optimized_cost_usd": round(optimized_cost, 2),
        "savings_usd": round(savings_usd, 2),
        "savings_percentage": round(savings_percentage, 1),
        "price_per_kwh": price_per_kwh,
        "optimized_price_per_kwh": new_price,
        "annual_savings_usd": round(savings_usd * 365, 2),
        "note": "annual figure assumes the calculation repeats daily; scale by runs/week if not",
    }
 
 
TOOL_KIT = [
    get_weather_forecast,
    get_electricity_prices,
    query_energy_usage,
    query_solar_generation,
    get_recent_energy_summary,
    search_energy_tips,
    calculate_energy_savings
]