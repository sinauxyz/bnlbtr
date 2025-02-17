import pandas as pd
import time
import json
import requests
import datetime
import os
from misc import get_header, get_json
from message import telegram_send_message
from binance import get_position, get_nickname, get_markprice

# Load UIDs from uids.json
with open('uids.json', 'r') as f:
    TARGETED_ACCOUNT_UIDS = json.load(f)

# Template URL for Binance account info
ACCOUNT_INFO_URL_TEMPLATE = 'https://www.binance.com/en/futures-activity/leaderboard/user?encryptedUid={}'

# Function to modify DataFrame
def modify_data(data) -> pd.DataFrame:
    # Pastikan data['otherPositionRetList'] ada dan tidak kosong
    if 'otherPositionRetList' not in data or not data['otherPositionRetList']:
        return pd.DataFrame()  # Kembalikan DataFrame kosong jika tidak ada data

    # Buat DataFrame dari otherPositionRetList
    position_list = data['otherPositionRetList']
    
    # Pastikan semua field yang diperlukan ada di setiap entri
    for position in position_list:
        if 'symbol' not in position:
            position['symbol'] = 'UNKNOWN'  # Berikan nilai default jika symbol tidak ada
        if 'amount' not in position:
            position['amount'] = 0.0  # Berikan nilai default jika amount tidak ada
        if 'leverage' not in position:
            position['leverage'] = 1.0  # Berikan nilai default jika leverage tidak ada
        if 'entryPrice' not in position:
            position['entryPrice'] = 0.0  # Berikan nilai default jika entryPrice tidak ada
        if 'markPrice' not in position:
            position['markPrice'] = 0.0  # Berikan nilai default jika markPrice tidak ada
        if 'pnl' not in position:
            position['pnl'] = 0.0  # Berikan nilai default jika pnl tidak ada
        if 'updateTimeStamp' not in position:
            position['updateTimeStamp'] = 0  # Berikan nilai default jika updateTimeStamp tidak ada

    # Buat DataFrame
    position = pd.DataFrame(position_list).set_index('symbol')
    
    # Hitung estimatedEntrySize dan tambahkan kolom baru
    position['estimatedEntrySize'] = round((abs(position['amount']) / position['leverage']) * position['entryPrice'], 2)
    position['pnl'] = round(position['pnl'], 2)
    
    # Tentukan posisi (LONG/SHORT)
    position.loc[(position['amount'] > 0), 'estimatedPosition'] = 'LONG'
    position.loc[(position['amount'] < 0), 'estimatedPosition'] = 'SHORT'
    
    # Format updateTime
    position['updateTime'] = position['updateTimeStamp'].apply(lambda x: datetime.datetime.fromtimestamp(x / 1000).strftime('%Y-%m-%d %H:%M:%S'))
    
    # Pilih kolom yang akan dikembalikan
    position_result = position[['estimatedPosition', 'leverage', 'estimatedEntrySize', 'amount',
                               'entryPrice', 'markPrice', 'pnl', 'updateTime']]
    return position_result

# Global variables to track previous positions
previous_symbols = {}
previous_position_results = {}
is_first_runs = {uid: True for uid in TARGETED_ACCOUNT_UIDS}

# Function to send new position message
def send_new_position_message(symbol, row, nickname):
    estimated_position = row['estimatedPosition']
    leverage = row['leverage']
    estimated_entry_size = row['estimatedEntrySize']
    entry_price = row['entryPrice']
    pnl = row['pnl']
    updatetime = row['updateTime']
    message = f"[<b>{nickname}</b>]\n<b>New position opened</b>\n\n" \
              f"Position: <b>{symbol} {estimated_position} {leverage}X</b>\n\n" \
              f"Base currency - USDT\n" \
              f"------------------------------\n" \
              f"Entry Price: {entry_price}\n" \
              f"Est. Entry Size: {estimated_entry_size}\n" \
              f"PnL: {pnl}\n\n" \
              f"Last Update:\n{updatetime} (UTC+0)\n" \
              f"<a href='{ACCOUNT_INFO_URL}'><b>VIEW PROFILE ON BINANCE</b></a>"
    telegram_send_message(message)

# Function to send closed position message
def send_closed_position_message(symbol, row, nickname):
    estimated_position = row['estimatedPosition']
    leverage = row['leverage']
    updatetime = row['updateTime']
    message = f"[<b>{nickname}</b>]\n<b>Position closed</b>\n\n" \
              f"Position: <b>{symbol} {estimated_position} {leverage}X</b>\n" \
              f"Current Price: {get_markprice(symbol)} USDT\n\n" \
              f"Last Update:\n{updatetime} (UTC+0)\n" \
              f"<a href='{ACCOUNT_INFO_URL}'><b>VIEW PROFILE ON BINANCE</b></a>"
    telegram_send_message(message)

# Function to send current positions
def send_current_positions(position_result, nickname):
    if position_result.empty:
        telegram_send_message(f"[<b>{nickname}</b>]\n<b>No positions found</b>")
    else:
        telegram_send_message(f"[<b>{nickname}</b>]\n<b>Current positions:</b>")
        for symbol, row in position_result.iterrows():
            estimated_position = row['estimatedPosition']
            leverage = row['leverage']
            estimated_entry_size = row['estimatedEntrySize']
            entry_price = row['entryPrice']
            pnl = row['pnl']
            updatetime = row['updateTime']
            message = f"Position: <b>{symbol} {estimated_position} {leverage}X</b>\n\n" \
                      f"Base currency - USDT\n" \
                      f"------------------------------\n" \
                      f"Entry Price: {entry_price}\n" \
                      f"Est. Entry Size: {estimated_entry_size}\n" \
                      f"PnL: {pnl}\n\n" \
                      f"Last Update:\n{updatetime} (UTC+0)\n" \
                      f"<a href='{ACCOUNT_INFO_URL}'><b>VIEW PROFILE ON BINANCE</b></a>"
            telegram_send_message(message)

# Main loop
while True:
    try:
        for TARGETED_ACCOUNT_UID in TARGETED_ACCOUNT_UIDS:
            ACCOUNT_INFO_URL = ACCOUNT_INFO_URL_TEMPLATE.format(TARGETED_ACCOUNT_UID)
            headers = get_header(ACCOUNT_INFO_URL)
            json_data = get_json(TARGETED_ACCOUNT_UID)

            # ========== PERBAIKAN UTAMA DI SINI ========== #
            response_nickname = get_nickname(TARGETED_ACCOUNT_UID)
            response = get_position(TARGETED_ACCOUNT_UID)

            if (
                response is not None 
                and response.get("success", False) 
                and response_nickname is not None 
                and response_nickname.get("success", False)
            ):
                nickname = response_nickname["data"]["nickName"]  # Definisikan nickname di sini
                print("API Response:", json.dumps(response, indent=2))
                leaderboard_data = response["data"]
                position_result = modify_data(leaderboard_data)
                print("Processed Data:\n", position_result)

                # Pindahkan SEMUA logika pengiriman pesan ke dalam blok ini
                new_symbols = position_result.index.difference(previous_symbols.get(TARGETED_ACCOUNT_UID, pd.Index([])))
                if not is_first_runs[TARGETED_ACCOUNT_UID] and not new_symbols.empty:
                    for symbol in new_symbols:
                        send_new_position_message(symbol, position_result.loc[symbol], nickname)

                closed_symbols = previous_symbols.get(TARGETED_ACCOUNT_UID, pd.Index([])).difference(position_result.index)
                if not is_first_runs[TARGETED_ACCOUNT_UID] and not closed_symbols.empty:
                    for symbol in closed_symbols:
                        if symbol in previous_position_results.get(TARGETED_ACCOUNT_UID, pd.DataFrame()).index:
                            send_closed_position_message(symbol, previous_position_results[TARGETED_ACCOUNT_UID].loc[symbol], nickname)

                if is_first_runs[TARGETED_ACCOUNT_UID]:
                    send_current_positions(position_result, nickname)

                previous_position_results[TARGETED_ACCOUNT_UID] = position_result.copy()
                previous_symbols[TARGETED_ACCOUNT_UID] = position_result.index.copy()
                is_first_runs[TARGETED_ACCOUNT_UID] = False

            else:
                print(f"⚠️ Gagal memproses UID {TARGETED_ACCOUNT_UID}")
                print("Nickname Response:", json.dumps(response_nickname, indent=2) if response_nickname else "No nickname response")
                print("Position Response:", json.dumps(response, indent=2) if response else "No position response")

        time.sleep(300)
    except Exception as e:
        print(f"Error occurred: {e}")
        message = f"Error occurred for UID <b>{TARGETED_ACCOUNT_UID}</b>:\n{e}\n\nRetrying after 60s"
        telegram_send_message(message)
        time.sleep(60)