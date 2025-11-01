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
PAL_TOKEN_ETH = "0xAB846Fb6C81370327e784Ae7CbB6d6a6af6Ff4BF"
PAL_TOKEN_SONIC = "0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac"

# Contract addresses
MIGRATION_CONTRACT_SONIC = "0x99fe40e501151e92f10ac13ea1c06083ee170363"
MIGRATION_CONTRACT_ETH = "0x3bA32287B008DdF3c5a38dF272369931E3030152"
DAO_ADDRESS = "0xe2a7de3c3190afd79c49c8e8f2fa30ca78b97dfd"
DEPLOYER_ADDRESS = "0x2cF08825066f01595705c204d8a2f403C2cb50cB"

# Event signatures
TRANSFER_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
LZ_COMPLETED_SIG = "0x877c1d3e3a57b5e2efc18188dcc66c21d13fb45b1729fc862810d63d04b0c44f"

# Excluded addresses
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
EXCLUDED_ADDRESSES = [
    DAO_ADDRESS.lower(),
    MIGRATION_CONTRACT_SONIC.lower(),
    MIGRATION_CONTRACT_ETH.lower(),
    DEPLOYER_ADDRESS.lower(),
    ZERO_ADDRESS
]

# Total supply
TREVEE_TOTAL_SUPPLY = 50000000

# ===== Helper Functions =====
def get_trevee_holders(rpc_url, trevee_token, start_block, max_range=10000):
    """Get holder count for TREVEE token on any chain with batching support"""
    try:
        # Get current block
        block_resp = requests.post(rpc_url, json={
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }, timeout=10)
        current_block = int(block_resp.json()["result"], 16)

        # Calculate range
        from_block = max(current_block - max_range, start_block)

        balances = defaultdict(int)
        batch_size = 5000  # Conservative batch size

        for batch_start in range(from_block, current_block + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, current_block)

            logs_response = requests.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [{
                    "fromBlock": hex(batch_start),
                    "toBlock": hex(batch_end),
                    "address": trevee_token,
                    "topics": [TRANSFER_SIG]
                }],
                "id": 1
            }, timeout=15)

            result = logs_response.json()
            if "error" in result:
                break

            logs = result.get("result", [])

            for log in logs:
                from_addr = "0x" + log["topics"][1][-40:]
                to_addr = "0x" + log["topics"][2][-40:]
                amount = int(log["data"], 16)

                if from_addr != ZERO_ADDRESS:
                    balances[from_addr.lower()] -= amount
                if to_addr != ZERO_ADDRESS:
                    balances[to_addr.lower()] += amount

        return len([addr for addr, bal in balances.items() if bal > 0])
    except Exception as e:
        print(f"Error getting holders: {e}")
        return 0

def get_token_supply(rpc_url, token_address):
    """Get total supply for a token"""
    try:
        supply_resp = requests.post(rpc_url, json={
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": token_address, "data": "0x18160ddd"}, "latest"],
            "id": 1
        }, timeout=10)
        return int(supply_resp.json().get("result", "0x0"), 16) / 10**18
    except:
        return 0

def get_migration_data():
    """Get PAL ’ TREVEE migration data from both chains"""
    try:
        # Prepare topics
        migration_topic_sonic = "0x" + MIGRATION_CONTRACT_SONIC[2:].lower().zfill(64)
        migration_topic_eth = "0x" + MIGRATION_CONTRACT_ETH[2:].lower().zfill(64)
        zero_topic = "0x" + "0" * 64

        # Get Sonic migrations (TREVEE and stkTREVEE)
        sonic_trevee_resp = requests.post(SONIC_RPC_URL, json={
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": "0x0",
                "toBlock": "latest",
                "address": TREVEE_TOKEN,
                "topics": [TRANSFER_SIG, migration_topic_sonic]
            }],
            "id": 1
        }, timeout=30)

        sonic_strevee_resp = requests.post(SONIC_RPC_URL, json={
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": "0x0",
                "toBlock": "latest",
                "address": STREVEE_TOKEN,
                "topics": [TRANSFER_SIG, zero_topic]
            }],
            "id": 1
        }, timeout=30)

        # Get Ethereum migrations
        eth_migration_resp = requests.post(ETH_RPC, json={
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": hex(19000000),
                "toBlock": "latest",
                "address": MIGRATION_CONTRACT_ETH,
                "topics": [LZ_COMPLETED_SIG]
            }],
            "id": 1
        }, timeout=30)

        sonic_trevee_logs = sonic_trevee_resp.json().get("result", [])
        sonic_strevee_logs = sonic_strevee_resp.json().get("result", [])
        eth_logs = eth_migration_resp.json().get("result", [])

        # Filter out excluded addresses
        def filter_logs(logs):
            filtered = []
            for log in logs:
                recipient = ("0x" + log["topics"][2][-40:]).lower()
                if recipient not in EXCLUDED_ADDRESSES:
                    filtered.append(log)
            return filtered

        sonic_trevee_logs = filter_logs(sonic_trevee_logs)
        sonic_strevee_logs = filter_logs(sonic_strevee_logs)

        # Calculate statistics
        all_migrations = sonic_trevee_logs + sonic_strevee_logs + eth_logs
        total_migrations = len(all_migrations)

        # Calculate total PAL migrated
        total_pal = 0
        amounts = []
        distribution = {
            '1-10k': 0,
            '10k-50k': 0,
            '50k-100k': 0,
            '100k-500k': 0,
            '500k+': 0
        }

        for log in all_migrations:
            amount = int(log["data"], 16) / 10**18
            total_pal += amount
            amounts.append(amount)

            # Distribution bucketing
            if amount < 10000:
                distribution['1-10k'] += 1
            elif amount < 50000:
                distribution['10k-50k'] += 1
            elif amount < 100000:
                distribution['50k-100k'] += 1
            elif amount < 500000:
                distribution['100k-500k'] += 1
            else:
                distribution['500k+'] += 1

        avg_migration = total_pal / total_migrations if total_migrations > 0 else 0
        max_migration = max(amounts) if amounts else 0

        return {
            "total_migrations": total_migrations,
            "total_pal": total_pal,
            "average": avg_migration,
            "max": max_migration,
            "distribution": distribution,
            "sonic_count": len(sonic_trevee_logs) + len(sonic_strevee_logs),
            "ethereum_count": len(eth_logs)
        }
    except Exception as e:
        print(f"Error getting migration data: {e}")
        return {
            "total_migrations": 0,
            "total_pal": 0,
            "average": 0,
            "max": 0,
            "distribution": {'1-10k': 0, '10k-50k': 0, '50k-100k': 0, '100k-500k': 0, '500k+': 0},
            "sonic_count": 0,
            "ethereum_count": 0
        }

def generate_mock_revenue_data():
    """Generate mock revenue data for the last 30 days"""
    today = datetime.now()
    labels = []
    values = []

    base_revenue = 5000
    for i in range(29, -1, -1):
        date = today - timedelta(days=i)
        labels.append(date.strftime('%m/%d'))

        # Generate semi-realistic revenue with trend
        daily_revenue = base_revenue + random.randint(-1000, 2000) + (29 - i) * 100
        values.append(max(0, daily_revenue))

    total_30d = sum(values)
    revenue_today = values[-1] if values else 0
    revenue_yesterday = values[-2] if len(values) > 1 else 0

    # Calculate change
    change_30d = random.uniform(15, 35)

    return {
        "total_30d": total_30d,
        "today": revenue_today,
        "yesterday": revenue_yesterday,
        "change_30d": change_30d,
        "history": {
            "labels": labels,
            "values": values
        }
    }

def generate_mock_buyback_data():
    """Generate mock buyback data for the last 30 days"""
    today = datetime.now()
    labels = []
    values = []

    for i in range(29, -1, -1):
        date = today - timedelta(days=i)
        labels.append(date.strftime('%m/%d'))

        # Generate buybacks (not every day)
        if random.random() > 0.6:  # 40% chance of buyback
            daily_buyback = random.randint(2000, 8000)
            values.append(daily_buyback)
        else:
            values.append(0)

    total_30d = sum(values)
    tokens_bought = total_30d / 0.05  # Assuming avg price of $0.05

    # Calculate change
    change_30d = random.uniform(20, 45)

    return {
        "total_30d": total_30d,
        "tokens_bought": tokens_bought,
        "avg_price": 0.05,
        "change_30d": change_30d,
        "history": {
            "labels": labels,
            "values": values
        }
    }

def generate_mock_price_history():
    """Generate mock price history"""
    labels = []
    values = []

    base_price = 0.045
    for i in range(24):
        labels.append(f"{i}:00")
        price_change = random.uniform(-0.005, 0.005)
        base_price = max(0.01, base_price + price_change)
        values.append(base_price)

    return {
        "labels": labels,
        "values": values
    }

def generate_mock_tvl_history():
    """Generate mock TVL history"""
    labels = []
    values = []

    base_tvl = 2000000
    for i in range(30):
        labels.append(f"Day {i+1}")
        tvl_change = random.randint(-50000, 100000)
        base_tvl = max(1000000, base_tvl + tvl_change)
        values.append(base_tvl)

    return {
        "labels": labels[-7:],  # Last 7 days
        "values": values[-7:]
    }

# ===== API Endpoints =====
@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Main endpoint that returns all dashboard metrics"""
    try:
        # Get Sonic data
        sonic_supply = get_token_supply(SONIC_RPC_URL, TREVEE_TOKEN)
        sonic_staked = get_token_supply(SONIC_RPC_URL, STREVEE_TOKEN)
        sonic_holders_trevee = get_trevee_holders(SONIC_RPC_URL, TREVEE_TOKEN, 0, max_range=100000)
        sonic_holders_strevee = get_trevee_holders(SONIC_RPC_URL, STREVEE_TOKEN, 0, max_range=100000)
        sonic_holders_total = len(set(list(range(sonic_holders_trevee)) + list(range(sonic_holders_strevee))))

        # Get Plasma data
        plasma_supply = get_token_supply(PLASMA_RPC, TREVEE_TOKEN)
        plasma_holders = 19  # Hardcoded per user request

        # Get Ethereum data
        eth_supply = get_token_supply(ETH_RPC, TREVEE_TOKEN)
        eth_holders = get_trevee_holders(ETH_RPC, TREVEE_TOKEN, 19000000, max_range=100000)

        # Get migration data
        migration_data = get_migration_data()

        # Calculate totals
        total_supply = TREVEE_TOTAL_SUPPLY
        circulating_supply = total_supply - sonic_staked  # Simplified

        # Mock token price and market cap
        token_price = 0.048
        market_cap = circulating_supply * token_price
        total_tvl = sonic_supply * token_price + plasma_supply * token_price + eth_supply * token_price

        # Total holders
        total_holders = sonic_holders_total + plasma_holders + eth_holders

        # Generate mock data
        revenue_data = generate_mock_revenue_data()
        buyback_data = generate_mock_buyback_data()
        price_history = generate_mock_price_history()
        tvl_history = generate_mock_tvl_history()

        # Build response
        response = {
            "token_price": token_price,
            "price_change_24h": random.uniform(-5, 8),
            "market_cap": market_cap,
            "mcap_rank": 1247,  # Mock rank
            "total_tvl": total_tvl,
            "total_holders": total_holders,
            "holders_change_24h": random.randint(2, 15),
            "total_supply": total_supply,
            "circulating_supply": circulating_supply,
            "total_staked": sonic_staked,
            "total_pal_migrated": migration_data["total_pal"],

            "chains": {
                "sonic": {
                    "supply": sonic_supply,
                    "staked": sonic_staked,
                    "holders": sonic_holders_total,
                    "pal_migrated": migration_data["total_pal"] * (migration_data["sonic_count"] / max(migration_data["total_migrations"], 1)),
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
                    "pal_migrated": migration_data["total_pal"] * (migration_data["ethereum_count"] / max(migration_data["total_migrations"], 1)),
                    "tvl": eth_supply * token_price
                }
            },

            "stk_supply": sonic_staked,
            "stakers_count": sonic_holders_strevee,

            "migration": migration_data,
            "migration_distribution": migration_data["distribution"],

            "revenue": revenue_data,
            "buyback": buyback_data,

            "price_history": price_history,
            "tvl_history": tvl_history,

            "timestamp": datetime.now().isoformat()
        }

        return jsonify(response)

    except Exception as e:
        print(f"Error in get_metrics: {e}")
        return jsonify({"error": str(e)}), 500

# Vercel serverless handler
def handler(request):
    with app.request_context(request.environ):
        try:
            return app.full_dispatch_request()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
