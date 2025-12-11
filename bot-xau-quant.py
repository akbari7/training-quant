# --- Scanner Pasar Crypto Real-Time 📡 ---
import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import datetime
from datetime import date

# ==========================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

# Error Handling
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError(f"❌ Error: Token-{TELEGRAM_TOKEN} atau Chat ID-{TELEGRAM_CHAT_ID} belum diset di Environment Variables!")
# ==========================================

def kirim_telegram(pesan):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

def cek_kondisi_pasar(symbol='GC=F'):
    print(f"Sedang menganalisis XAU ... Mohon tunggu ⏳")
    try:
        # 1. Ambil data Live (period='1y' biar aman buat hitung SMA50)
        df = yf.download(symbol, period='1y', interval='1d', progress=False)

        if len(df) < 50:
            print("Data tidak cukup untuk analisis.")
            return

        # 2. Hitung Indikator (Resep Rahasia Kita)
        # Konversi ke float untuk menghindari warning
        close_prices = df['Close'].astype(float)

        df['SMA_20'] = close_prices.rolling(window=20).mean()
        df['SMA_50'] = close_prices.rolling(window=50).mean()

        # RSI Manual
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # 3. Ambil Data Terakhir (HARI INI)
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] # Kemarin (buat cek silangan)

        # Ambil nilai scalar (angka tunggal)
        harga_now = float(last_row['Close'])
        rsi_now = float(last_row['RSI'])
        sma20_now = float(last_row['SMA_20'])
        sma50_now = float(last_row['SMA_50'])

        sma20_prev = float(prev_row['SMA_20'])
        sma50_prev = float(prev_row['SMA_50'])
        rsi_prev = float(prev_row['RSI'])

        # Format Tanggal
        tanggal = last_row.name.strftime('%Y-%m-%d')
        full_tanggal = last_row.name + datetime.timedelta(hours=7)
        fix_tanggal = full_tanggal.strftime('%Y-%m-%d %H:%M')

        # --- HITUNG PERUBAHAN HARGA HARI INI (%) ---
        harga_kemarin = float(prev_row['Close'])
        perubahan_persen = ((harga_now - harga_kemarin) / harga_kemarin) * 100

        # --- TAMPILAN DASHBOARD ---
        print("\n" + "="*40)
        print(f"  LAPORAN HARIAN ROBOT ({tanggal})")
        print("="*40)
        print(f"💎 Aset       : XAU")
        print(f"💵 Harga Saat Ini : ${harga_now:,.2f}")
        print(f"📊 RSI Saat Ini   : {rsi_now:.2f} (Zona: {'PANAS 🔥' if rsi_now > 70 else 'DINGIN ❄️' if rsi_now < 30 else 'NETRAL 😐'})")
        print("-" * 40)

        # Cek Tren (SMA)
        if sma20_now > sma50_now:
            trend = "BULLISH (Naik) 📈"
        else:
            trend = "BEARISH (Turun) 📉"
        print(f"Arah Tren    : {trend}")
        print("-" * 40)

        # Tambahan info di console biar kelihatan
        print(f"📉 Perubahan Hari Ini: {perubahan_persen:.2f}%")

        # --- KEPUTUSAN ROBOT (BRAIN) ---
        print("🤖 REKOMENDASI AI:")

        signal_msg = ""

        # PRIORITY ALERT: CRASH WARNING (Turun > 1%) 🚨
        if perubahan_persen <= -1.0:
            print(">>> ⚠️ PERINGATAN: HARGA JATUH > 1%")
            signal_msg = f"\n\n🚨 *ALERT: DROP {perubahan_persen:.2f}%* \nXAU diskon besar atau Crash? Cek chart!"

        # Logic BUY: Golden Cross Baru Saja Terjadi
        elif (sma20_prev < sma50_prev) and (sma20_now > sma50_now):
            print(">>> SINYAL BELI KUAT! (GOLDEN CROSS) 🚀")
            print("Saran: Masuk sekarang, pasang Stop Loss 5%.")
            signal_msg = "\n\n🚀 *SINYAL: GOLDEN CROSS!* \nTren mulai naik. Cek market bos!"

        # Logic SELL: RSI Breakdown
        elif (rsi_prev > 70) and (rsi_now < 70):
            print(">>> SINYAL JUAL! (RSI BREAKDOWN) ⚠️")
            print("Saran: Take Profit sekarang sebelum harga longsor.")
            signal_msg = "\n\n⚠️ *WARNING: OVERBOUGHT* \nHati-hati pucuk. Jangan FOMO Tapi Boleh Jual."

        # Logic HOLD
        else:
            print(">>> WAIT & SEE (TUNGGU) ☕")
            if sma20_now > sma50_now:
                if rsi_now > 70:
                    signal_msg = "\n\n☕ *Wait & See* \nRSI sudah Overbought. Siap-siap jual."
                    print("Warning: Hati-hati, RSI sudah Overbought. Siap-siap jual.")
                else:
                    signal_msg = "\n\n☕ *Wait & See* \nKalau punya barang, TAHAN."
                    print("Status: Sedang dalam tren naik. Kalau punya barang, TAHAN.")
            else:
                signal_msg = "\n\n☕ *Wait & See* \nTren Turun. Jangan Tangkap Pisau Jatuh."
                print("Status: Tren sedang turun. Jangan menangkap pisau jatuh.")
        
        # Kirim!
        if signal_msg:
            # --- SUSUN PESAN TELEGRAM ---
            # Kita bikin format pesan yang cantik
            header = f"🤖 *LAPORAN {fix_tanggal}: XAU*"
            body = f"💵 Harga: ${harga_now:,.6f}\n📊 RSI: {rsi_now:.2f}"
            full_pesan = header + body + signal_msg
            kirim_telegram(full_pesan)
            print(f"✅ Laporan XAU terkirim ke HP!")
        else:
            print(f"⚠️ Laporan XAU tidak dikirim ke HP!")

    except Exception as e:
        print(f"Mohon untuk cek simbol yang di cari: {e}")

# Jalankan Scanner
cek_kondisi_pasar('GC=F')