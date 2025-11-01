from flask import Flask, jsonify
import requests
from collections import defaultdict
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# ===== Constants =====
SONIC_RPC_URL = "https://rpc.soniclabs.com"
PLASMA_RPC = "https://rpc.plasma.to"
ETH_RPC = "https://eth-mainnet.g.alchemy.com/v2/ph0FUrSi6-8SvDzvJYtc1"

# Token addresses
TREVEE_TOKEN = "0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac"
STREVEE_TOKEN = "0x3ba32287b008ddf3c5a38df272369931e3030152"

# Total supply
TREVEE_TOTAL_SUPPLY = 50000000

# ===== Helper Functions =====
def get_token_supply(rpc_url, token_address):
    """Get total supply for a token"""
    try:
        supply_resp = requests.post(rpc_url, json={
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": token_address, "data": "0x18160ddd"}, "latest"],
            "id": 1
        }, timeout=10)
        result = supply_resp.json().get("result", "0x0")
        return int(result, 16) / 10**18
    except Exception as e:
        print(f"Error getting supply for {token_address}: {e}")
        return 0

def get_token_balance(rpc_url, token_address, holder_address):
    """Get token balance for a specific address"""
    try:
        # balanceOf function signature + padded address
        data = "0x70a08231" + holder_address[2:].zfill(64)
        balance_resp = requests.post(rpc_url, json={
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": token_address, "data": data}, "latest"],
            "id": 1
        }, timeout=10)
        result = balance_resp.json().get("result", "0x0")
        return int(result, 16) / 10**18
    except Exception as e:
        print(f"Error getting balance: {e}")
        return 0

def get_holder_count_estimate(rpc_url, token_address, recent_blocks=50000):
    """Get approximate holder count from recent transfer events"""
    try:
        # Get current block
        block_resp = requests.post(rpc_url, json={
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }, timeout=10)
        current_block = int(block_resp.json()["result"], 16)
        from_block = max(0, current_block - recent_blocks)

        # Get transfer events
        logs_response = requests.post(rpc_url, json={
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": hex(from_block),
                "toBlock": "latest",
                "address": token_address,
                "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]
            }],
            "id": 1
        }, timeout=30)

        logs = logs_response.json().get("result", [])
        unique_addresses = set()

        for log in logs:
            if len(log["topics"]) >= 3:
                from_addr = "0x" + log["topics"][1][-40:]
                to_addr = "0x" + log["topics"][2][-40:]
                if from_addr != "0x0000000000000000000000000000000000000000":
                    unique_addresses.add(from_addr.lower())
                if to_addr != "0x0000000000000000000000000000000000000000":
                    unique_addresses.add(to_addr.lower())

        return len(unique_addresses)
    except Exception as e:
        print(f"Error estimating holders: {e}")
        return 0

def generate_mock_price_history():
    """Generate realistic price history"""
    labels = []
    values = []
    base_price = 0.045

    for i in range(24):
        labels.append(f"{i}:00")
        price_change = random.uniform(-0.002, 0.003)
        base_price = max(0.01, base_price + price_change)
        values.append(round(base_price, 6))

    return {"labels": labels, "values": values}

def generate_mock_tvl_history(current_tvl):
    """Generate TVL history based on current TVL"""
    labels = []
    values = []
    base_tvl = current_tvl * 0.85  # Start 15% lower

    for i in range(7):
        labels.append(f"Day {i+1}")
        tvl_change = random.uniform(-0.05, 0.1) * base_tvl
        base_tvl = max(current_tvl * 0.7, base_tvl + tvl_change)
        values.append(int(base_tvl))

    return {"labels": labels, "values": values}

def get_coingecko_data():
    """Fetch real price data from CoinGecko (if available)"""
    # For now, return mock data since TREVEE might not be on CoinGecko yet
    # When listed, replace with actual API call
    return {
        "price": 0.048,
        "price_change_24h": random.uniform(-5, 8),
        "market_cap_rank": None
    }

def generate_revenue_data():
    """Generate revenue data (mock for now - replace with real protocol fee data)"""
    labels = []
    values = []

    for i in range(30):
        date = (datetime.now() - timedelta(days=29-i))
        labels.append(date.strftime('%m/%d'))
        daily_revenue = random.randint(3000, 8000)
        values.append(daily_revenue)

    total_30d = sum(values)
    return {
        "total_30d": total_30d,
        "today": values[-1] if values else 0,
        "yesterday": values[-2] if len(values) > 1 else 0,
        "change_30d": random.uniform(15, 35),
        "history": {"labels": labels[-7:], "values": values[-7:]}
    }

def generate_buyback_data():
    """Generate buyback data (mock for now - replace with real buyback tracking)"""
    labels = []
    values = []

    for i in range(30):
        date = (datetime.now() - timedelta(days=29-i))
        labels.append(date.strftime('%m/%d'))
        if random.random() > 0.6:
            daily_buyback = random.randint(2000, 6000)
            values.append(daily_buyback)
        else:
            values.append(0)

    total_30d = sum(values)
    return {
        "total_30d": total_30d,
        "tokens_bought": total_30d / 0.05,
        "avg_price": 0.05,
        "change_30d": random.uniform(20, 45),
        "history": {"labels": labels[-7:], "values": values[-7:]}
    }

# ===== API Endpoints =====
@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Main endpoint that returns all dashboard metrics"""
    try:
        # Get Sonic data
        sonic_supply = get_token_supply(SONIC_RPC_URL, TREVEE_TOKEN)
        sonic_staked = get_token_supply(SONIC_RPC_URL, STREVEE_TOKEN)
        sonic_holders = get_holder_count_estimate(SONIC_RPC_URL, TREVEE_TOKEN, recent_blocks=50000)

        # Get Plasma data
        plasma_supply = get_token_supply(PLASMA_RPC, TREVEE_TOKEN)
        plasma_holders = 19  # Hardcoded per previous requirement

        # Get Ethereum data
        eth_supply = get_token_supply(ETH_RPC, TREVEE_TOKEN)
        eth_holders = get_holder_count_estimate(ETH_RPC, TREVEE_TOKEN, recent_blocks=50000)

        # Calculate totals
        total_supply = TREVEE_TOTAL_SUPPLY
        circulating_supply = total_supply - sonic_staked

        # Get price data
        price_data = get_coingecko_data()
        token_price = price_data["price"]

        # Calculate market cap and TVL
        market_cap = circulating_supply * token_price
        total_tvl = (sonic_supply + plasma_supply + eth_supply) * token_price

        # Total holders (approximate)
        total_holders = sonic_holders + plasma_holders + eth_holders

        # Generate historical data
        price_history = generate_mock_price_history()
        tvl_history = generate_mock_tvl_history(total_tvl)
        revenue_data = generate_revenue_data()
        buyback_data = generate_buyback_data()

        # Build response
        response = {
            "token_price": token_price,
            "price_change_24h": price_data["price_change_24h"],
            "market_cap": market_cap,
            "mcap_rank": price_data["market_cap_rank"],
            "total_tvl": total_tvl,
            "total_holders": total_holders,
            "holders_change_24h": random.randint(2, 15),
            "total_supply": total_supply,
            "circulating_supply": circulating_supply,
            "total_staked": sonic_staked,

            "chains": {
                "sonic": {
                    "supply": sonic_supply,
                    "staked": sonic_staked,
                    "holders": sonic_holders,
                    "tvl": sonic_supply * token_price
                },
                "plasma": {
                    "supply": plasma_supply,
                    "holders": plasma_holders,
                    "tvl": plasma_supply * token_price
                },
                "ethereum": {
                    "supply": eth_supply,
                    "holders": eth_holders,
                    "tvl": eth_supply * token_price
                }
            },

            "stk_supply": sonic_staked,
            "stakers_count": get_holder_count_estimate(SONIC_RPC_URL, STREVEE_TOKEN, recent_blocks=30000),

            "revenue": revenue_data,
            "buyback": buyback_data,

            "price_history": price_history,
            "tvl_history": tvl_history,

            "timestamp": datetime.now().isoformat()
        }

        return jsonify(response)

    except Exception as e:
        print(f"Error in get_metrics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Vercel serverless handler
def handler(request):
    with app.request_context(request.environ):
        try:
            return app.full_dispatch_request()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# For local testing
if __name__ == '__main__':
    app.run(debug=True, port=5000)
