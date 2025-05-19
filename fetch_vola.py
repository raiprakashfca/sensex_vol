import yfinance as yf
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json


def fetch_sensex_1m():
    """Fetch today's 1-minute SENSEX bars (OHLC) in IST and return a DataFrame."""
    ticker = yf.Ticker("^BSESN")
    df = ticker.history(interval="1m", period="1d").dropna()
    df.index = df.index.tz_convert("Asia/Kolkata")
    return df[["Open", "High", "Low", "Close"]]


def add_volatility(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Compute annualized rolling volatility on log returns.

    Parameters:
    - df: DataFrame with a "Close" column.
    - window: look-back period in minutes.

    Returns:
    - DataFrame with new columns "ret" (log returns) and "vola" (annualized volatility).
    """
    df = df.copy()
    df["ret"] = np.log(df["Close"] / df["Close"].shift())
    annual_factor = np.sqrt(252 * 6.5 * 60)  # trading days * hours * minutes
    df["vola"] = df["ret"].rolling(window).std() * annual_factor
    return df.dropna()


def save_to_excel(df: pd.DataFrame, path: str = "sensex_volatility.xlsx") -> str:
    """Save DataFrame to an Excel file and return its path."""
    df.to_excel(path)
    return path


def write_to_gsheet(df: pd.DataFrame, sheet_key: str, worksheet: str = "Sheet1") -> None:
    """
    Write DataFrame (including timestamp index) to a Google Sheet,
    using service-account credentials stored in the GSPREAD_CRED_JSON environment variable.

    Parameters:
    - df: DataFrame with DateTime index.
    - sheet_key: the Google Sheet ID.
    - worksheet: the worksheet/tab name.
    """
    # Load credentials from env-var
    cred_json = os.environ.get("GSPREAD_CRED_JSON")
    if not cred_json:
        raise ValueError("Environment variable GSPREAD_CRED_JSON not set")
    creds_dict = json.loads(cred_json)
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    # Authorize and write
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_key)
    ws = sheet.worksheet(worksheet)
    ws.clear()
    rows = [df.reset_index().columns.tolist()] + df.reset_index().astype(str).values.tolist()
    ws.update(rows)
