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

            all_time_pairs = {}
            chart_data = []
            
            # Process daily data
            for day in days:
                date_str = day["day_date"]
                markets = day.get("markets", {})
                
                day_spot_vol = 0.0
                day_futures_vol = 0.0
                
                for pair, vol_str in markets.items():
                    vol = float(vol_str)
                    
                    # Track All-Time Totals per pair
                    all_time_pairs[pair] = all_time_pairs.get(pair, 0) + vol
                    
                    # Split Spot vs Futures for the Chart
                    if "/" in pair:
                        day_spot_vol += vol
                    else:
                        day_futures_vol += vol
                
                chart_data.append({
                    "date": date_str,
                    "spot": round(day_spot_vol, 2),
                    "futures": round(day_futures_vol, 2),
                    "total": round(day_spot_vol + day_futures_vol, 2)
                })

            # 1. GENERATE SUMMARY FILE
            # Get All-Time Top 5
            top_all_time = sorted(all_time_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Get Today's Data (Last item in array)
            latest_day = days[-1]
            latest_markets = latest_day.get("markets", {})
            
            # Separate Today's Spot and Futures
            today_spot = {k: float(v) for k, v in latest_markets.items() if "/" in k}
            today_futures = {k: float(v) for k, v in latest_markets.items() if "-" in k}
            
            top_today_spot = sorted(today_spot.items(), key=lambda x: x[1], reverse=True)[:5]
            top_today_futures = sorted(today_futures.items(), key=lambda x: x[1], reverse=True)[:5]

            summary = {
                "updated_at": datetime.now().isoformat(),
                "all_time_stats": {
                    "total_combined_volume": round(sum(all_time_pairs.values()), 2),
                    "top_5_pairs": [{"pair": k, "volume": round(v, 2)} for k, v in top_all_time]
                },
                "today_stats": {
                    "date": latest_day["day_date"],
                    "top_5_spot": [{"pair": k, "volume": round(v, 2)} for k, v in top_today_spot],
                    "top_5_futures": [{"pair": k, "volume": round(v, 2)} for k, v in top_today_futures]
                }
            }

            # Save Files
            with open(SUMMARY_FILE, 'w') as f:
                json.dump(summary, f, indent=2)
            
            with open(CHART_FILE, 'w') as f:
                json.dump(chart_data, f, indent=2)

            print(f"✅ Volume Summary and Chart updated using {len(days)} days of data.")

if __name__ == "__main__":
    asyncio.run(main())
