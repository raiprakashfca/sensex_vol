import streamlit as st
import mplfinance as mpf
from fetch_vola import fetch_sensex_1m, add_volatility, save_to_excel, write_to_gsheet
import yfinance as yf
import pandas as pd
import numpy as np
import os
import json

# ----------- Streamlit Page Config -----------
st.set_page_config(page_title="🔍 SENSEX Volatility Tracker", layout="wide")

@st.cache_data(ttl=60)
def get_minute_data(window: int = 30):
    """Fetch and compute intraday volatility with a rolling window (minutes)."""
    df = fetch_sensex_1m()
    return add_volatility(df, window=window)

@st.cache_data
def get_daily_vix_analog(window_days: int = 30):
    """Compute a 30-day (default) historical volatility on daily SENSEX close prices."""
    df = yf.Ticker("^BSESN").history(interval="1d", period=f"{window_days*3}d").dropna()
    # Ensure IST tz for consistency
    df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
    # Daily log returns
    df['ret'] = np.log(df['Close'] / df['Close'].shift())
    # Annualize: sqrt(252 trading days)
    df['vol_30d'] = df['ret'].rolling(window_days).std() * np.sqrt(252)
    return df.dropna()

# --- Sidebar controls ---
st.sidebar.header("⚙️ Settings")
interval = st.sidebar.selectbox("Chart Interval", ["1 Minute", "5 Minutes", "15 Minutes", "1 Hour", "1 Day"], index=0)
window = st.sidebar.slider("Intraday Vol Window (minutes)", min_value=5, max_value=120, value=30)
vix_window = st.sidebar.slider("VIX Analog Window (days)", min_value=10, max_value=60, value=30)

# Map interval labels to pandas freq
freq_map = {"1 Minute":"1T","5 Minutes":"5T","15 Minutes":"15T","1 Hour":"1H","1 Day":"1D"}

# --- Fetch data ---
df_min = get_minute_data(window)
df_daily = get_daily_vix_analog(vix_window)

# --- Resample for price and vola charts ---
price_ohlc = df_min[["Open","High","Low","Close"]].resample(freq_map[interval]).agg({
    "Open":"first","High":"max","Low":"min","Close":"last"}).dropna()
vola_ohlc = df_min['vola'].resample(freq_map[interval]).ohlc().dropna()

# --- Display charts ---
st.title("📊 SENSEX Volatility Dashboard")

st.subheader(f"Intraday Price & Volatility ({interval}, {window}‑min vol window)")
# Price chart
fig1, _ = mpf.plot(price_ohlc, type="candle", style="yahoo", mav=(5,10), returnfig=True, figsize=(10,4))
st.pyplot(fig1)
# Volatility chart
fig2, _ = mpf.plot(vola_ohlc, type="candle", style="charles", returnfig=True, figsize=(10,4))
st.pyplot(fig2)

# --- VIX analog chart ---
st.subheader(f"VIX Analog: {vix_window}-day Historical Volatility")
st.line_chart(df_daily['vol_30d'])

# --- Raw data table ---
st.subheader("🔢 Raw Intraday Data")
st.dataframe(df_min)

# --- Export buttons ---
col1, col2 = st.columns(2)
with col1:
    if st.button("📥 Download Intraday Excel"):
        path = save_to_excel(df_min)
        with open(path, "rb") as f:
            st.download_button("Download .xlsx", f, file_name="sensex_intraday_vol.xlsx")
with col2:
    sheet_key = os.environ.get("GSHEET_KEY") or st.secrets.get("GSHEET_KEY")
    if st.button("↪️ Send Intraday to Google Sheet"):
        write_to_gsheet(df_min, sheet_key)
        st.success("Intraday data sent!")

# --- VIX analog export ---
if st.button("📥 Download VIX Analog Data"):
    df_vix = df_daily[['vol_30d']]
    df_vix.to_excel("sensex_vix_analog.xlsx")
    with open("sensex_vix_analog.xlsx", "rb") as f:
        st.download_button("Download VIX .xlsx", f, file_name="sensex_vix_analog.xlsx")
