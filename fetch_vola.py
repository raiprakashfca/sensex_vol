import yfinance as yf
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def fetch_sensex_1m():
    """Fetch today's 1-minute SENSEX bars (OHLC) and return a DataFrame."""
    ticker = yf.Ticker("^BSESN")
    df = ticker.history(interval="1m", period="1d").dropna()
    # Ensure the index is in Asia/Kolkata timezone
    df.index = df.index.tz_convert("Asia/Kolkata")
    return df[["Open", "High", "Low", "Close"]]


def add_volatility(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Compute annualized rolling volatility on log returns.

    Parameters:
    - df: DataFrame with at least a "Close" column.
    - window: look-back period in minutes (rolling window size).

    Returns:
    - DataFrame with new column "vola" (volatility) and "ret" (log returns).
    """
    df = df.copy()
    df["ret"] = np.log(df["Close"] / df["Close"].shift())
    # Annualize factor: sqrt(252 trading days * 6.5 hrs/day * 60 minutes)
    annual_factor = np.sqrt(252 * 6.5 * 60)
    df["vola"] = df["ret"].rolling(window).std() * annual_factor
    return df.dropna()


def save_to_excel(df: pd.DataFrame, path: str = "sensex_volatility.xlsx") -> str:
    """
    Save DataFrame to an Excel file and return the file path.
    """
    df.to_excel(path)
    return path


def write_to_gsheet(df: pd.DataFrame,
                    sheet_key: str,
                    worksheet: str = "Sheet1",
                    credentials_path: str = "credentials.json") -> None:
    """
    Write DataFrame (including timestamp index) to a Google Sheet.

    Parameters:
    - df: DataFrame to write (index as Timestamp).
    - sheet_key: the Google Sheet ID.
    - worksheet: the name of the worksheet/tab.
    - credentials_path: path to the service-account JSON key.
    """
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)
    sh = client.open_by_key(sheet_key)
    ws = sh.worksheet(worksheet)
    # Clear existing content
    ws.clear()
    # Prepare rows: header + data
    rows = [df.reset_index().columns.tolist()] + df.reset_index().astype(str).values.tolist()
    ws.update(rows)
