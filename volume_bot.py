import aiohttp
import asyncio
import json
from datetime import datetime

API_URL = "https://mainnet-data.sodex.dev/api/v1/dashboard/volume?start_date=2026-01-05&end_date=2030-01-01&market_type=all"
SUMMARY_FILE = "volume_summary.json"
CHART_FILE = "volume_chart.json"

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as response:
            if response.status != 200:
                print("❌ API Error")
                return
            
            raw_data = await response.json()
            days = raw_data.get("data", {}).get("data", [])

            # Dictionaries to track All-Time totals per pair
            all_time_spot_pairs = {}
            all_time_futures_pairs = {}
            total_combined_volume = 0.0
            chart_data = []
            
            # Process every day in the dataset
            for day in days:
                date_str = day["day_date"]
                markets = day.get("markets", {})
                
                day_spot_vol = 0.0
                day_futures_vol = 0.0
                
                for pair, vol_str in markets.items():
                    vol = float(vol_str)
                    total_combined_volume += vol
                    
                    # Sort into Spot vs Futures for All-Time tracking
                    if "/" in pair:
                        all_time_spot_pairs[pair] = all_time_spot_pairs.get(pair, 0) + vol
                        day_spot_vol += vol
                    elif "-" in pair:
                        all_time_futures_pairs[pair] = all_time_futures_pairs.get(pair, 0) + vol
                        day_futures_vol += vol
                
                # Full day-by-day resolution for the graph
                chart_data.append({
                    "day": date_str,
                    "spot_vol": round(day_spot_vol, 2),
                    "futures_vol": round(day_futures_vol, 2),
                    "total_day_vol": round(day_spot_vol + day_futures_vol, 2)
                })

            # --- CALCULATE LEADERBOARDS ---
            # All-Time Spot Top 5
            top_5_all_time_spot = sorted(all_time_spot_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
            # All-Time Futures Top 5
            top_5_all_time_futures = sorted(all_time_futures_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Get Today's Top 5 (Latest day in array)
            latest_day = days[-1]
            latest_markets = latest_day.get("markets", {})
            today_spot = {k: float(v) for k, v in latest_markets.items() if "/" in k}
            today_futures = {k: float(v) for k, v in latest_markets.items() if "-" in k}
            
            top_today_spot = sorted(today_spot.items(), key=lambda x: x[1], reverse=True)[:5]
            top_today_futures = sorted(today_futures.items(), key=lambda x: x[1], reverse=True)[:5]

            # --- GENERATE SUMMARY FILE ---
            summary = {
                "updated_at": datetime.now().isoformat(),
                "all_time_stats": {
                    "total_combined_volume": round(total_combined_volume, 2),
                    "top_5_spot": [{"pair": k, "volume": round(v, 2)} for k, v in top_5_all_time_spot],
                    "top_5_futures": [{"pair": k, "volume": round(v, 2)} for k, v in top_5_all_time_futures]
                },
                "today_stats": {
                    "date": latest_day["day_date"],
                    "top_5_spot": [{"pair": k, "volume": round(v, 2)} for k, v in top_today_spot],
                    "top_5_futures": [{"pair": k, "volume": round(v, 2)} for k, v in top_today_futures]
                }
            }

            with open(SUMMARY_FILE, 'w') as f:
                json.dump(summary, f, indent=2)
            
            with open(CHART_FILE, 'w') as f:
                json.dump(chart_data, f, indent=2)

            print(f"✅ Volume Sync Complete. Total Volume: {round(total_combined_volume, 2)}")

if __name__ == "__main__":
    asyncio.run(main())
