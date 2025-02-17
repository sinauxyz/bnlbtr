import requests
import time
from message import telegram_send_message

# RapidAPI Key (simpan langsung di script)
RAPIDAPI_KEY = "7ccaedf5b1msh05d118514652180p1c45f8jsne50e34c1891f"  # Ganti dengan API key Anda

def get_position(encrypted_uid: str, max_retries=5):
    """
    Mendapatkan posisi trading dari API pihak ketiga.
    
    :param encrypted_uid: UID terenkripsi dari akun yang ingin dilacak.
    :param max_retries: Jumlah maksimum percobaan ulang jika terjadi kesalahan.
    :return: Response dari API atau None jika gagal setelah max_retries.
    """
    url = "https://binance-futures-leaderboard1.p.rapidapi.com/v1/getOtherPosition"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "binance-futures-leaderboard1.p.rapidapi.com"
    }
    querystring = {"encryptedUid": encrypted_uid, "tradeType": "PERPETUAL"}

    retry_count = 0
    while retry_count <= max_retries:
        try:
            response = requests.get(url, headers=headers, params=querystring)
            if response.status_code == 200:
                return response.json()  # Mengembalikan data JSON jika sukses
            else:
                print(f"Error: {response.status_code} - {response.text}")
                telegram_send_message(f"Error: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Connection error occurred: {e}")
            telegram_send_message(f"Connection error occurred: {e}")
            if retry_count >= max_retries:
                telegram_send_message("Max retry count reached. Waiting for 10 minutes before next try...")
                time.sleep(600)
                retry_count = 0
            else:
                print("Retrying in 5 seconds...")
                time.sleep(5)
                retry_count += 1
    return None

def get_nickname(encrypted_uid: str, max_retries=5):
    """
    Mendapatkan informasi dasar leaderboard (termasuk nickname) dari API pihak ketiga.
    
    :param encrypted_uid: UID terenkripsi dari akun yang ingin dilacak.
    :param max_retries: Jumlah maksimum percobaan ulang jika terjadi kesalahan.
    :return: Response dari API atau None jika gagal setelah max_retries.
    """
    url = "https://binance-futures-leaderboard1.p.rapidapi.com/v1/getOtherLeaderboardBaseInfo"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "binance-futures-leaderboard1.p.rapidapi.com"
    }
    querystring = {"encryptedUid": encrypted_uid}

    retry_count = 0
    while retry_count <= max_retries:
        try:
            response = requests.get(url, headers=headers, params=querystring)
            if response.status_code == 200:
                return response.json()  # Mengembalikan data JSON jika sukses
            else:
                print(f"Error: {response.status_code} - {response.text}")
                telegram_send_message(f"Error: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Connection error occurred: {e}")
            telegram_send_message(f"Connection error occurred: {e}")
            if retry_count >= max_retries:
                telegram_send_message("Max retry count reached. Waiting for 10 minutes before next try...")
                time.sleep(600)
                retry_count = 0
            else:
                print("Retrying in 5 seconds...")
                time.sleep(5)
                retry_count += 1
    return None

def get_markprice(symbol):
    """
    Mendapatkan harga mark (mark price) dari Binance Futures API.
    
    :param symbol: Simbol trading (misalnya, BTCUSDT).
    :return: Harga mark atau pesan kesalahan jika gagal.
    """
    api_url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    req_data = requests.get(api_url, params={"symbol": symbol})
    try:
        data = req_data.json()
        return data['markPrice']
    except Exception:
        return "Market price retrieval error"