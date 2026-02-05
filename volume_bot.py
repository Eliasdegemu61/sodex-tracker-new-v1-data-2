import aiohttp
import asyncio
import json
from datetime import datetime

# UPDATED: Correct API starting from 2024-01-01
API_URL = "https://mainnet-data.sodex.dev/api/v1/dashboard/volume?start_date=2024-01-01&end_date=2030-01-01&market_type=all"
SUMMARY_FILE = "volume_summary.json"
CHART_FILE = "volume_chart.json"

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as response:
            if response.status != 200:
                print(f"❌ API Error: {response.status}")
                return
            
            payload = await response.json()
            days_array = payload.get("data", {}).get("data", [])

            if not days_array:
                print("⚠️ No data found in the response.")
                return

            all_time_spot_pairs = {}
            all_time_futures_pairs = {}
            grand_total_calculated = 0.0
            chart_entries = []
            
            print(f"🚀 Processing {len(days_array)} days of history starting from 2024...")

            for day_data in days_array:
                current_day_date = day_data["day_date"]
                market_pairs = day_data.get("markets", {})
                
                day_spot_total = 0.0
                day_futures_total = 0.0
                
                # Iterate through every pair in the day
                for pair, val in market_pairs.items():
                    try:
                        v = float(val)
                        grand_total_calculated += v
                        
                        # Spot vs Futures Logic
                        if "/" in pair:
                            all_time_spot_pairs[pair] = all_time_spot_pairs.get(pair, 0) + v
                            day_spot_total += v
                        else:
                            all_time_futures_pairs[pair] = all_time_futures_pairs.get(pair, 0) + v
                            day_futures_total += v
                    except:
                        continue

                # Add every single day to the chart array
                chart_entries.append({
                    "day": current_day_date,
                    "spot_vol": round(day_spot_total, 2),
                    "futures_vol": round(day_futures_total, 2),
                    "total_day_vol": round(day_spot_total + day_futures_total, 2)
                })

            # --- CALCULATE FINAL LEADERBOARDS ---
            top_spot_all_time = sorted(all_time_spot_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
            top_futures_all_time = sorted(all_time_futures_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Latest Day Snapshot (Today's Top 5)
            latest = days_array[-1]
            latest_mkt = latest.get("markets", {})
            t_spot = {k: float(v) for k, v in latest_mkt.items() if "/" in k}
            t_futures = {k: float(v) for k, v in latest_mkt.items() if "/" not in k}

            summary_output = {
                "updated_at": datetime.now().isoformat(),
                "all_time_stats": {
                    "total_combined_volume": round(grand_total_calculated, 2),
                    "top_5_spot": [{"pair": p, "volume": round(v, 2)} for p, v in top_spot_all_time],
                    "top_5_futures": [{"pair": p, "volume": round(v, 2)} for p, v in top_futures_all_time]
                },
                "today_stats": {
                    "date": latest["day_date"],
                    "top_5_spot": [{"pair": k, "volume": round(v, 2)} for k, v in sorted(t_spot.items(), key=lambda x: x[1], reverse=True)[:5]],
                    "top_5_futures": [{"pair": k, "volume": round(v, 2)} for k, v in sorted(t_futures.items(), key=lambda x: x[1], reverse=True)[:5]]
                }
            }

            # Save Output
            with open(SUMMARY_FILE, 'w') as f:
                json.dump(summary_output, f, indent=2)
            with open(CHART_FILE, 'w') as f:
                json.dump(chart_entries, f, indent=2)

            print(f"✅ Calculation Finished.")
            print(f"📊 New Total Combined Volume: ${round(grand_total_calculated, 2):,}")

if __name__ == "__main__":
    asyncio.run(main())
