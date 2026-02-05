import aiohttp
import asyncio
import json
from datetime import datetime

# API URL covering the full historical range
API_URL = "https://mainnet-data.sodex.dev/api/v1/dashboard/volume?start_date=2026-01-05&end_date=2030-01-01&market_type=all"
SUMMARY_FILE = "volume_summary.json"
CHART_FILE = "volume_chart.json"

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as response:
            if response.status != 200:
                print(f"❌ API Error: {response.status}")
                return
            
            raw_data = await response.json()
            # Access the nested list of days
            days_list = raw_data.get("data", {}).get("data", [])

            if not days_list:
                print("⚠️ No data found in API response.")
                return

            # Tracking variables
            all_time_spot_pairs = {}
            all_time_futures_pairs = {}
            grand_total_combined = 0.0
            chart_data = []
            
            # --- PROCESS EVERY DAY ---
            for day_entry in days_list:
                date_str = day_entry["day_date"]
                markets = day_entry.get("markets", {})
                
                day_spot_sum = 0.0
                day_futures_sum = 0.0
                
                # --- PROCESS EVERY INDIVIDUAL PAIR ---
                # We ignore day_entry["total"] and day_entry["cumulative"]
                for pair_name, volume_value in markets.items():
                    try:
                        vol = float(volume_value)
                    except ValueError:
                        continue
                    
                    # 1. Add to the Grand Total
                    grand_total_combined += vol
                    
                    # 2. Categorize and track All-Time stats
                    if "/" in pair_name:
                        # SPOT PAIR (e.g., BTC/USDC)
                        all_time_spot_pairs[pair_name] = all_time_spot_pairs.get(pair_name, 0) + vol
                        day_spot_sum += vol
                    else:
                        # FUTURES PAIR (e.g., BTC-USD)
                        all_time_futures_pairs[pair_name] = all_time_futures_pairs.get(pair_name, 0) + vol
                        day_futures_sum += vol
                
                # Save this day's calculated totals for the graph
                chart_data.append({
                    "day": date_str,
                    "spot_vol": round(day_spot_sum, 2),
                    "futures_vol": round(day_futures_sum, 2),
                    "total_day_vol": round(day_spot_sum + day_futures_sum, 2)
                })

            # --- CALCULATE FINAL LEADERBOARDS ---
            # All-Time Top 5 Spot
            top_spot_all_time = sorted(all_time_spot_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
            # All-Time Top 5 Futures
            top_futures_all_time = sorted(all_time_futures_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Get Today's specific Top 5 (using the last day in the list)
            latest_day = days_list[-1]
            latest_markets = latest_day.get("markets", {})
            
            t_spot = {k: float(v) for k, v in latest_markets.items() if "/" in k}
            t_futures = {k: float(v) for k, v in latest_markets.items() if "/" not in k}
            
            top_today_spot = sorted(t_spot.items(), key=lambda x: x[1], reverse=True)[:5]
            top_today_futures = sorted(t_futures.items(), key=lambda x: x[1], reverse=True)[:5]

            # --- PREPARE SUMMARY OUTPUT ---
            summary = {
                "updated_at": datetime.now().isoformat(),
                "all_time_stats": {
                    "total_combined_volume": round(grand_total_combined, 2),
                    "top_5_spot": [{"pair": k, "volume": round(v, 2)} for k, v in top_spot_all_time],
                    "top_5_futures": [{"pair": k, "volume": round(v, 2)} for k, v in top_futures_all_time]
                },
                "today_stats": {
                    "date": latest_day["day_date"],
                    "top_5_spot": [{"pair": k, "volume": round(v, 2)} for k, v in top_today_spot],
                    "top_5_futures": [{"pair": k, "volume": round(v, 2)} for k, v in top_today_futures]
                }
            }

            # --- SAVE FILES ---
            with open(SUMMARY_FILE, 'w') as f:
                json.dump(summary, f, indent=2)
            
            with open(CHART_FILE, 'w') as f:
                json.dump(chart_data, f, indent=2)

            print(f"✅ Success! Processed {len(days_list)} days.")
            print(f"📊 Recalculated Grand Total: {round(grand_total_combined, 2)}")

if __name__ == "__main__":
    asyncio.run(main())
