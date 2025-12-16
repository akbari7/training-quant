# --- Scanner Pasar Crypto Universal (via CoinGecko) 🦎 ---
# Support token kecil kayak DMC, PEPE, dll.
import json
import os
import requests
from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime
import time
import datetime
from datetime import date

# ==========================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
ISDAILY = os.getenv('ISDAILY')
ISSHORT = os.getenv('ISSHORT')
ISDCA = os.getenv('ISDCA')
PERCENTENV = os.getenv('MINPERCENT')
MINPERCENT = float(PERCENTENV) if PERCENTENV else 0.0
COINID = os.getenv('COINID')

# Error Handling
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError(f"❌ Error: Token-{TELEGRAM_TOKEN} atau Chat ID-{TELEGRAM_CHAT_ID} belum diset di Environment Variables!")
# ==========================================

# Inisialisasi CoinGecko
cg = CoinGeckoAPI()

def kirim_telegram(pesan):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

# Nama file database mini kita
STATE_FILE = 'price-database.json'

def load_state():
    """Baca data terakhir dari file JSON"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {} # Kalau file ga ada, return kosong

def save_state(new_data):
    """Update file JSON dengan data baru"""
    # Baca dulu data lama biar ga ketimpa semua
    current_data = load_state()
    # Update key yang berubah aja
    current_data.update(new_data)
    
    with open(STATE_FILE, 'w') as f:
        json.dump(current_data, f, indent=4)
        print("💾 Data berhasil disimpan ke JSON lokal!")

def get_fear_greed_index():
    try:
         # API gratis dari alternative.me
        url_fng = "https://api.alternative.me/fng/"
        response_fng = requests.get(url_fng, timeout=10)
        data_fng = response_fng.json()
        
        value_fng = data_fng['data'][0]['value']
        status_fng = data_fng['data'][0]['value_classification']

        # Tambahin emoji biar gak garing
        emoji_fng = "😱" # Extreme Fear
        if int(value_fng) >= 45: emoji_fng = "😐" # Neutral
        if int(value_fng) >= 60: emoji_fng = "🙂" # Greed
        if int(value_fng) >= 75: emoji_fng = "🤑" # Extreme Greed
        
        return f"{value_fng} - {status_fng} {emoji_fng}"
    except Exception as e:
        print(f"Gagal ambil Fear & Greed: {e}")
        return "N/A"


def cek_kondisi_pasar_micin(coin_id='delorean'):
    # Note: coin_id harus ID dari CoinGecko (bukan symbol).
    # Contoh: 'bitcoin', 'ethereum', 'delorean' (untuk DMC)

    print(f"🕵️ Sedang melacak {coin_id.upper()} di CoinGecko... Tunggu bentar ⏳")

    try:
        # 1. Di Awal Fungsi: BACA MEMORY
        state = load_state()
        # Ambil harga beli terakhir (kalau ada)
        last_buy_price = state.get(f"{coin_id}_buy_price", 0) 
        has_pos = state.get(f"{coin_id}_has_position", False)
        print(f"🧐 Status Terakhir {coin_id}: Punya Barang? {has_pos} | Harga Modal: ${last_buy_price}")
        
        # 1. Ambil Data Historis (90 hari terakhir cukup buat SMA50)
        # vs_currency='usd' artinya harga dalam Dollar
        raw_data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days='100')

        # 2. Rapikan Data ke Pandas DataFrame
        prices = raw_data['prices'] # Isinya [timestamp, price]
        df = pd.DataFrame(prices, columns=['timestamp', 'Close'])

        # Konversi Timestamp (ms) ke Tanggal yang bisa dibaca
        df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('Date', inplace=True)

        # 3. Hitung Indikator (Resep Quant Kita)
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()

        # Hitung RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # Cek apakah datanya cukup?
        if len(df) < 50:
            print("⚠️ Data historis kurang panjang untuk menghitung SMA 50.")
            print(f"Umur data cuma {len(df)} hari.")
            return

        # 4. Ambil Data Terakhir
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        harga_now = float(last_row['Close'])
        rsi_now = float(last_row['RSI'])
        sma20_now = float(last_row['SMA_20'])
        sma50_now = float(last_row['SMA_50'])

        harga_prev = float(prev_row['Close'])
        sma20_prev = float(prev_row['SMA_20'])
        sma50_prev = float(prev_row['SMA_50'])
        rsi_prev = float(prev_row['RSI'])

        tanggal = last_row.name.strftime('%Y-%m-%d')
        full_tanggal = last_row.name + datetime.timedelta(hours=7)
        fix_tanggal = full_tanggal.strftime('%Y-%m-%d %H:%M')

        # --- HITUNG PERUBAHAN HARGA HARI INI (%) ---
        perubahan_persen = ((harga_now - harga_prev) / harga_prev) * 100

        # --- TAMPILAN DASHBOARD ---
        print("\n" + "="*45)
        print(f"  LAPORAN HARIAN ROBOT: {coin_id.upper()}")
        print(f"  Tanggal Data: {tanggal}")
        print("="*45)
        print(f"💵 Harga Saat Ini : ${harga_now:.6f}") # Pakai 6 desimal buat token murah
        print(f"📊 RSI Saat Ini   : {rsi_now:.2f}")

        # Info Zona RSI
        if rsi_now > 70:
            print("   Status RSI     : 🔥 OVERBOUGHT (Hati-hati Pucuk!)")
        elif rsi_now < 30:
            print("   Status RSI     : ❄️ OVERSOLD (Diskon Besar?)")
        else:
            print("   Status RSI     : 😐 NETRAL")

        print("-" * 45)

        # Cek Tren
        tren = ''
        if sma20_now > sma50_now:
            print("📈 Tren Besar     : BULLISH (Naik)")
            tren = '📈 BULLISH'
        else:
            print("📉 Tren Besar     : BEARISH (Turun)")
            tren = '📉 BEARISH'

        print("-" * 45)
        print("🤖 SARAN ROBOT:")

        # --- 🛡️ VOLATILITY SHIELD LOGIC ---
        # 1. Hitung Daily Returns (perubahan harian dalam %)
        df['returns'] = df['Close'].pct_change() * 100
        
        # 2. Hitung Volatilitas (Standard Deviation dari 30 hari terakhir)
        vol_harian = df['returns'].tail(30).std()
        
        # 3. Hitung Rekomendasi Stop Loss (2x Volatilitas)
        # Contoh: Jika vol DMC 11%, maka SL adalah 22%
        rekomendasi_sl_persen = vol_harian * 2
        harga_stop_loss = harga_now * (1 - (rekomendasi_sl_persen / 100))
        # ----------------------------------

        # --- D. SUSUN PESAN TELEGRAM ---
        # Kita bikin format pesan yang cantik
        signal_msg = ""

        # LOGIKA SINYAL
        signal_found = False

        # PRIORITY ALERT: CRASH WARNING (Turun > 1%) 🚨
        if PERCENTENV:
            lessP = perubahan_persen <= -(MINPERCENT)
            moreP = perubahan_persen >= -(MINPERCENT)
            print(f">>> 📉 percent : {lessP}")
            print(f">>> 📈 percent : {moreP}")
            if lessP:
                print(f">>> ⚠️ PERINGATAN: HARGA JATUH > {MINPERCENT}%")
                signal_found = True
                signal_msg = f"\n\n🚨 *ALERT: DROP {perubahan_persen:.2f}%* \ndiskon besar atau Crash? Cek chart!"

        if not signal_found:
            
            # =====================================================
            # 🔴 STRATEGI 1: BITCOIN (THE BEAR HUNTER - SHORT)
            # =====================================================
            if ISSHORT:
                
                # A. LOGIKA ENTRY SHORT (Pasang Posisi Jual)
                # 1. Death Cross (SMA20 motong ke BAWAH SMA50)
                if (sma20_prev > sma50_prev) and (sma20_now < sma50_now):
                    signal_msg = "\n\n📉 *SINYAL: OPEN SHORT!* \nDeath Cross terjadi. Tren valid turun."
                    signal_found = True
                
                # 2. RSI Pucuk (Overbought > 70)
                elif rsi_now > 70:
                    signal_msg = "\n\n📉 *SINYAL: SHORT SCALP!* \nRSI Pucuk (>70). Siap-siap koreksi."
                    signal_found = True

                # B. LOGIKA EXIT SHORT (Ambil Untung / Kabur)
                # 1. RSI Oversold (Murah banget, bahaya kalau masih Short)
                elif rsi_now < 30:
                    signal_msg = "\n\n✅ *SINYAL: TAKE PROFIT (COVER SHORT)* \nRSI Oversold (<30). Bungkus profit Short kamu!"
                    signal_found = True
                
                # 2. Golden Cross (Tren balik jadi Bullish)
                elif (sma20_prev < sma50_prev) and (sma20_now > sma50_now):
                    signal_msg = "\n\n🚨 *SINYAL: CLOSE SHORT / SWITCH LONG* \nTren berubah Bullish (Golden Cross)."
                    signal_found = True

            # =====================================================
            # 🟢 STRATEGI 2: DMC & PAXG (THE ACCUMULATOR - DCA)
            # =====================================================
            elif ISDCA:
                
                # 1. Zona Diskon Besar (Lumpsum)
                if rsi_now < 30:
                    signal_msg = f"\n\n💎 *SINYAL: LUMPSUM BUY*\nRSI {rsi_now:.2f} (Oversold). Diskon besar, serok!"
                    signal_found = True
                    
                # 2. Zona Cicil (DCA) - Kita set di bawah 45 biar sering nyicil
                elif rsi_now < 45:
                    signal_msg = f"\n\n💰 *SINYAL: DCA BUY*\nRSI {rsi_now:.2f} (Murah). Waktunya nyicil santai."
                    signal_found = True

            # =====================================================
            # ⚪ STRATEGI 3: UMUM (BACKUP / STANDARD)
            # =====================================================
            else:
                # Ini logika lama (Golden Cross biasa)
                # Buat koin lain kalau nanti kamu nambah (misal: Solana)
                if (sma20_prev < sma50_prev) and (sma20_now > sma50_now):
                    save_state({
                        f"{coin_id}_buy_price": harga_now,
                        f"{coin_id}_has_position": True
                    })
                    signal_msg = "\n\n🚀 *SINYAL: GOLDEN CROSS!* \nTren mulai naik."
                    signal_found = True

                elif (rsi_prev > 70) and (rsi_now < 70):
                    save_state({
                        f"{coin_id}_buy_price": 0,
                        f"{coin_id}_has_position": False
                    })
                    signal_msg = "\n\n⚠️ *WARNING: OVERBOUGHT* \nJual sekarang."
                    signal_found = True

            # =====================================================
            # ☕ LOGIKA WAIT & SEE (KALAU GAK ADA SINYAL DI ATAS)
            # =====================================================
            if not signal_found and ISDAILY:
                # A. Kalau Mode SHORT
                if ISSHORT:
                    if sma20_now < sma50_now:
                        signal_msg = "\n\n☕ *Wait & See (Short Mode)* \nHold posisi Short. Tren masih turun."
                    else:
                        signal_msg = "\n\n☕ *Wait & See (Neutral)* \nTren Bullish, jangan Short dulu."
                
                # B. Kalau Mode DCA
                elif ISDCA:
                    signal_msg = "\n\n☕ *Wait & See (Pantau)* \nHarga belum cukup murah buat DCA."
                
                # C. Mode Standar
                else:
                    signal_msg = "\n\n☕ *Wait & See* \nPasar sideways/belum ada sinyal."

        # Kirim!
        if (signal_msg):
            # --- 📈 PROFIT / LOSS TRACKER LOGIC ---
            pnl_msg = "Tidak ada posisi"
            checkLastPrice = float(last_buy_price) if last_buy_price else 0.0
            
            if has_pos and last_buy_price > 0:
                # Hitung persentase P&L
                pnl_persen = ((harga_now - last_buy_price) / last_buy_price) * 100
                
                # Tentukan emoji & tanda
                if pnl_persen > 0:
                    pnl_msg = f"+{pnl_persen:.2f}% 🚀"
                elif pnl_persen < 0:
                    pnl_msg = f"{pnl_persen:.2f}% 🔻"
                else:
                    pnl_msg = "0.00% ➖"
                
                # Tambahkan harga modal di sampingnya biar jelas
                pnl_msg = f"{pnl_msg} (Modal: ${last_buy_price:,.6f})"
                
            # Ambil sentimen pasar global
            fng_index = get_fear_greed_index()

            actionCoin = ''
            if ISSHORT:
                actionCoin = 'SHORT - '
            if ISDCA:
                actionCoin = 'DCA - '
            header = f"🤖 *{actionCoin}LAPORAN {fix_tanggal}: {coin_id.upper()}*"
            body = f"💵 Harga: ${harga_now:,.6f}\n📊 RSI: {rsi_now:.2f}({tren})"
            body += f"\n🎭 Sentimen Global: {fng_index}"
            if checkLastPrice > 0:
                body += f"\n🧐 Status Posisi: {pnl_msg}"
            body += f"\n🛡️ *Volatility Shield:* {vol_harian:.2f}%"
            body += f"\n🛑 *Safe Stop Loss:* {rekomendasi_sl_persen:.1f}% (~${harga_stop_loss:,.6f})"
            full_pesan = header + body + signal_msg
            kirim_telegram(full_pesan)
            print(f"✅ Laporan {coin_id} terkirim ke HP!")
        else:
            print(f"✅ Laporan {coin_id} tidak dikirim ke HP!")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Tips: Cek apakah ID koin benar? (Cari di coingecko.com)")
# --- CARA PAKAI ---
# Ganti 'delorean' dengan ID koin lain kalau mau.
# Contoh: 'bitcoin', 'solana', 'pepe', 'shiba-inu'
cek_kondisi_pasar_micin(COINID)