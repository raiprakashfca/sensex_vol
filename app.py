import yfinance as yf
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json


def fetch_sensex_1m():
    """Fetch today's 1-minute SENSEX bars (OHLC) and return a DataFrame in IST."""
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
    factor = np.sqrt(252 * 6.5 * 60)
    df["vola"] = df["ret"].rolling(window).std() * factor
    return df.dropna()


def save_to_excel(df: pd.DataFrame, path: str = "sensex_volatility.xlsx") -> str:
    """Save DataFrame to an Excel file and return its path."""
    df.to_excel(path)
    return path


def write_to_gsheet(df: pd.DataFrame,
                    sheet_key: str,
                    worksheet: str = "Sheet1") -> None:
    """
    Write DataFrame into a Google Sheet using credentials from an environment variable.

    Environment:
    - GSPREAD_CRED_JSON: JSON string of service-account credentials

    Parameters:
    - df: DataFrame (index as Timestamp)
    - sheet_key: Google Sheet ID
    - worksheet: tab name
    """
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    cred_json = os.environ.get("GSPREAD_CRED_JSON")
    if not cred_json:
        raise ValueError("Environment variable GSPREAD_CRED_JSON not set")
    creds_dict = json.loads(cred_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_key)
    ws = sheet.worksheet(worksheet)
    ws.clear()
    rows = [df.reset_index().columns.tolist()] + df.reset_index().astype(str).values.tolist()
    ws.update(rows)
