import streamlit as st
import mplfinance as mpf
from fetch_vola import fetch_sensex_1m, add_volatility, save_to_excel, write_to_gsheet
import os

# ----------- Streamlit Page Config -----------
st.set_page_config(page_title="🔍 SENSEX Volatility Tracker", layout="wide")

@st.cache(ttl=60)
def get_data():
    """Fetch and compute volatility."""
    df = fetch_sensex_1m()
    return add_volatility(df)

# Load data
df = get_data()

# --- Interval selector ---
interval_labels = {
    "1 Minute": "1T",
    "5 Minutes": "5T",
    "15 Minutes": "15T",
    "1 Hour": "1H",
    "1 Day": "1D",
}
choice = st.selectbox("📊 Chart Interval", list(interval_labels.keys()), index=0)
freq = interval_labels[choice]

# --- Resample price and volatility ---
price_ohlc = (
    df[["Open", "High", "Low", "Close"]]
    .resample(freq)
    .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"})
    .dropna()
)
vola_ohlc = df["vola"].resample(freq).ohlc().dropna()

# --- Title ---
st.header(f"1️⃣ SENSEX {choice} Price & Volatility")

# --- Price Candlestick Chart ---
fig_price, _ = mpf.plot(
    price_ohlc,
    type="candle",
    style="yahoo",
    mav=(5, 10),
    volume=False,
    returnfig=True,
    figsize=(10, 4)
)
st.pyplot(fig_price)

# --- Volatility Candlestick Chart ---
fig_vola, _ = mpf.plot(
    vola_ohlc,
    type="candle",
    style="charles",
    returnfig=True,
    figsize=(10, 4)
)
st.pyplot(fig_vola)

# --- Raw Data Table ---
st.subheader("🔢 Raw Data (1-min bars with volatility)")
st.dataframe(df)

# --- Export Buttons ---
col1, col2 = st.columns(2)
with col1:
    if st.button("📥 Download Excel"):
        path = save_to_excel(df)
        with open(path, "rb") as f:
            st.download_button(
                label="Download .xlsx",
                data=f,
                file_name="sensex_volatility.xlsx"
            )
with col2:
    # Prefer environment var over secrets for CI
    sheet_key = os.environ.get("GSHEET_KEY") or st.secrets.get("GSHEET_KEY")
    if st.button("↪️ Send to Google Sheet"):
        write_to_gsheet(df, sheet_key)
        st.success("Sent to Google Sheet!")
