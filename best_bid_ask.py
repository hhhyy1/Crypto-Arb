#!/usr/bin/env python3
import os
import glob
import json
from datetime import datetime
import asyncio
import aiofiles
from main import record_bids

record_bid = {}


async def get_latest_line(file_path):
    """
    read the last line of the file
    """
    if not os.path.exists(file_path):
        return None
    loop = asyncio.get_running_loop()
    with open(file_path, "r", encoding="utf-8") as f:
        lines = await loop.run_in_executor(None, f.readlines)
        lines = [line.strip() for line in lines if line.strip()]
        if not lines:
            return None
        return lines[-1]


async def get_latest_update_file(exchange_dir):
    pattern = os.path.join(exchange_dir, "orderbook_*update-*.jsonl")
    loop = asyncio.get_running_loop()
    files = await loop.run_in_executor(None, glob.glob, pattern)
    if not files:
        return None

    def extract_date(filename):
        #  orderbook_{pair}-update-{date}.jsonl
        base = os.path.basename(filename)
        parts = base.split("-")
        if len(parts) < 2:
            return None
        date_part = parts[-1].replace(".jsonl", "")
        try:
            return datetime.fromisoformat(date_part)
        except Exception:
            return None

    files_with_dates = [(f, extract_date(f)) for f in files]
    files_with_dates = [(f, d) for f, d in files_with_dates if d is not None]
    if not files_with_dates:
        return None

    files_with_dates.sort(key=lambda x: x[1], reverse=True)
    return files_with_dates[0][0]


async def get_latest_update_for_exchange(exchange, pair):
    exchange_dir = exchange
    today = datetime.now().date().isoformat()
    # get the data of today
    file_name = f"orderbook_{pair}-update-{today}.jsonl"
    file_path = os.path.join(exchange_dir, file_name)
    if not os.path.exists(file_path):
        file_path = await get_latest_update_file(exchange_dir)
    if not file_path:
        return None

    latest_line = await get_latest_line(file_path)
    if latest_line:
        try:
            return json.loads(latest_line)
        except json.JSONDecodeError:
            print(f" failed to fetch data from {file_path} ")
            return None
    return None


"""
main part --dealing with the data format

"""


async def get_best_bid_and_ask(exchange, pair):
    update = await get_latest_update_for_exchange(exchange, pair)
    if not update:
        return None, None, None, None, None

    ts = update.get("ts") if "ts" in update else update.get("E")

    if exchange == "binance":
        bids = update.get("b", [])
        asks = update.get("a", [])
        if bids and asks:
            best_bid = bids[0][0]
            best_bid_volume = bids[0][1]
            best_ask = asks[0][0]
            best_ask_volume = asks[0][1]
            return best_bid, best_ask, ts, best_bid_volume, best_ask_volume
        return None, None, ts, None, None

    elif exchange == "okx":
        data_list = update.get("data", [])
        if data_list and isinstance(data_list, list):
            data_entry = data_list[0]
            bids = data_entry.get("bids", [])
            asks = data_entry.get("asks", [])
            if bids and asks:
                best_bid = bids[0][0]
                best_bid_volume = bids[0][1]
                best_ask = asks[0][0]
                best_ask_volume = asks[0][1]
                return best_bid, best_ask, ts, best_bid_volume, best_ask_volume
        return None, None, ts, None, None

    elif exchange == "bybit":
        data_entry = update.get("data", {})
        bids = data_entry.get("b", [])
        asks = data_entry.get("a", [])
        if bids and asks:
            best_bid = bids[0][0]
            best_bid_volume = bids[0][1]
            best_ask = asks[0][0]
            best_ask_volume = asks[0][1]
            return best_bid, best_ask, ts, best_bid_volume, best_ask_volume
        return None, None, ts, None, None

    elif exchange == "bitget":
        data_list = update.get("data", [])
        if data_list and isinstance(data_list, list):
            data_entry = data_list[0]
            bids = data_entry.get("bids", [])
            asks = data_entry.get("asks", [])
            if bids and asks:
                best_bid = bids[0][0]
                best_bid_volume = bids[0][1]
                best_ask = asks[0][0]
                best_ask_volume = asks[0][1]
                return best_bid, best_ask, ts, best_bid_volume, best_ask_volume
        return None, None, ts, None, None

    else:
        print(f"{exchange} data process is wrong")
        return None, None, ts, None, None


async def get_global_best_bid_and_ask(pair):
    exchanges = ["binance", "okx", "bybit", "bitget"]
    best_bid_dict = {}
    best_ask_dict = {}
    best_bid_ts_dict = {}
    best_ask_ts_dict = {}
    best_bid_volume_dict = {}
    best_ask_volume_dict = {}

    tasks = [get_best_bid_and_ask(exch, pair) for exch in exchanges]
    results = await asyncio.gather(*tasks)

    for exch, (bid, ask, ts, bid_volume, ask_volume) in zip(exchanges, results):
        if bid is not None and ask is not None:
            best_bid_dict[exch] = bid
            best_ask_dict[exch] = ask
            best_bid_ts_dict[exch] = ts
            best_ask_ts_dict[exch] = ts
            best_bid_volume_dict[exch] = bid_volume
            best_ask_volume_dict[exch] = ask_volume

    if best_bid_dict and best_ask_dict:
        global_best_bid = max(best_bid_dict.values())
        global_best_ask = min(best_ask_dict.values())
        global_best_bid_exchange = max(best_bid_dict, key=best_bid_dict.get)
        global_best_ask_exchange = min(best_ask_dict, key=best_ask_dict.get)
        global_best_bid_ts = best_bid_ts_dict[global_best_bid_exchange]
        global_best_ask_ts = best_ask_ts_dict[global_best_ask_exchange]
        global_best_bid_volume = best_bid_volume_dict[global_best_bid_exchange]
        global_best_ask_volume = best_ask_volume_dict[global_best_ask_exchange]
        top_20_global_best_bid = sorted(
            best_bid_dict.items(), key=lambda x: x[1], reverse=True
        )[:20]
        top_20_global_best_ask = sorted(
            best_ask_dict.items(), key=lambda x: x[1], reverse=True
        )[:20]
        top_20_global_best_bid_volume = sorted(
            best_bid_volume_dict.items(), key=lambda x: x[1], reverse=True
        )[:20]
        top_20_global_best_ask_volume = sorted(
            best_ask_volume_dict.items(), key=lambda x: x[1], reverse=True
        )[:20]
    else:
        global_best_bid, global_best_ask = None, None
        global_best_bid_exchange, global_best_ask_exchange = None, None
        global_best_bid_ts, global_best_ask_ts = None, None
        global_best_bid_volume, global_best_ask_volume = None, None

    # return the global best bid and ask and the best bid and ask for each exchange
    return {
        "global_best_bid": global_best_bid,
        "global_best_ask": global_best_ask,
        "global_best_bid_exchange": global_best_bid_exchange,
        "global_best_ask_exchange": global_best_ask_exchange,
        "global_best_bid_ts": global_best_bid_ts,
        "global_best_ask_ts": global_best_ask_ts,
        "global_best_bid_volume": global_best_bid_volume,
        "global_best_ask_volume": global_best_ask_volume,
        "exchanges_bid": best_bid_dict,
        "exchanges_ask": best_ask_dict,
        "exchanges_bid_ts": best_bid_ts_dict,
        "exchanges_ask_ts": best_ask_ts_dict,
        "exchanges_bid_volume": best_bid_volume_dict,
        "exchanges_ask_volume": best_ask_volume_dict,
        "top_20_global_best_bids": top_20_global_best_bid,
        "top_20_global_best_asks": top_20_global_best_ask,
        "top_20_global_best_bid_volume": top_20_global_best_bid_volume,
        "top_20_global_best_ask_volume": top_20_global_best_ask_volume,
    }


# load bid-ask logs
async def save_msg_to_file(msg):
    async with aiofiles.open("bid_ask.jsonl", mode="a") as f:
        await f.write(json.dumps(msg) + "\n")


async def perform_arbitrage(pair, record_bids, msg):
    # fetch all the data
    data = await get_global_best_bid_and_ask(pair)
    best_bid = data["global_best_bid"]
    best_ask = data["global_best_ask"]

    if best_bid is None or best_ask is None:
        print("not enough data to perform arbitrage")
        return

    best_bid = float(best_bid)
    best_ask = float(best_ask)
    # calculate the spread
    spread = best_bid - best_ask

    # minima profit theshold
    min_profit_threshold = 0.01  #

    if spread > min_profit_threshold:
        msg += f"Arbitrage Opportunity Exists, Best Ask: {best_ask}, Best Bid: {best_bid}, Profit Spread: {spread}\n"

        #  data["exchanges_ask"]  data["exchanges_bid"]
        sell_exchange = data["global_best_bid_exchange"]
        buy_exchange = data["global_best_ask_exchange"]
        best_bid_ts = data["global_best_bid_ts"]
        best_ask_ts = data["global_best_ask_ts"]
        best_bid_volume = data["global_best_bid_volume"]
        best_ask_volume = data["global_best_ask_volume"]

        msg += f"suggesting long {buy_exchange} , short {sell_exchange} on {pair}\n"
        msg += f"Best bid timestamp: {best_bid_ts}, volume: {best_bid_volume}\n"
        msg += f"Best ask timestamp: {best_ask_ts}, volume: {best_ask_volume}\n"

        # Only update record_bids if there's an arbitrage opportunity
        time_now = datetime.now()
        record_bid = {
            "ts": datetime.fromtimestamp(best_bid_ts / 1000),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "best_bid_volume": best_bid_volume,
            "best_ask_volume": best_ask_volume,
            "best_ask_exchange": sell_exchange,
            "best_bid_exchange": buy_exchange,
            "pair": pair,
            "top_20_global_best_bids": data["top_20_global_best_bids"],
            "top_20_global_best_asks": data["top_20_global_best_asks"],
            "top_20_global_best_bid_volume": data["top_20_global_best_bid_volume"],
            "top_20_global_best_ask_volume": data["top_20_global_best_ask_volume"],
        }
        record_bids[str(time_now)] = record_bid

    else:
        msg += "no arbitrage opportunity\n"

    await save_msg_to_file(msg)
    return msg


async def main(record_bids):
    msg = ""
    exchanges = {
        "binance": "btcusdt",  # Binance using lowercase for pair
        "okx": "BTC-USDT",
        "bybit": "BTCUSDT",
        "bitget": "BTCUSDT",
    }

    tasks = [
        get_latest_update_for_exchange(exchange, pair)
        for exchange, pair in exchanges.items()
    ]
    results = await asyncio.gather(*tasks)
    for (exchange, pair), update in zip(exchanges.items(), results):
        retries = 0
        while update is None and retries < 3:
            print(
                f"{exchange.upper()} failed to fetch {pair} update data. Retrying in 1 second..."
            )
            await asyncio.sleep(1)
            update = await get_latest_update_for_exchange(exchange, pair)
            retries += 1

        if update is None:
            print(
                f"{exchange.upper()} failed to fetch {pair} update data after {retries} retries. Exiting with error."
            )
            return None

    arbitrage_pair = "BTCUSDT"  ## pairs to check for arbitrage
    msg = await perform_arbitrage(arbitrage_pair, record_bids, msg)
    return record_bids if len(record_bids) != 0 else None


if __name__ == "__main__":
    asyncio.run(main())
