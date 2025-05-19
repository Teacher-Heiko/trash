# PYTHON CURRENCY CONVERTER

# Import necessary libraries
import tkinter as tk  # GUI framework
from tkinter import ttk, messagebox  # GUI widgets and message pop-ups
import requests  # Used to call exchange rate APIs
import yfinance as yf  # Fetch financial market data (Gold, Bitcoin)
import pandas as pd  # Handle tabular data for charts and tables
from datetime import datetime, timedelta  # Manage date ranges
import time  # Used to control caching behavior
import os  # File system operations
import json  # Read/write cached JSON files
import matplotlib.pyplot as plt  # For plotting charts
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Embed charts into Tkinter

# URL of the public exchange rate API (free and no key required)
EXCHANGE_API = "https://api.exchangerate-api.com/v4/latest/"
# File where cached rates will be saved
CACHE_FILE = "rates_cache.json"

# Supported currencies, including crypto and precious metals
CURRENCIES = sorted([
    "USD", "THB", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SEK", "NZD",
    "Bitcoin", "XAU (Gold/Oz)"
])

# Cache values for offline mode and API throttling
cached_rates = None
last_fetch_time = 0

# Function to fetch live exchange rates or load from cache
def get_rates():
    global cached_rates, last_fetch_time

    # If cached data is still valid (within 5 minutes), use it
    if time.time() - last_fetch_time < 300 and cached_rates:
        return cached_rates

    try:
        # Fetch fiat currency rates
        fx_data = requests.get(EXCHANGE_API + "USD").json()
        if "rates" not in fx_data:
            raise Exception("Exchange API error")
        rates = fx_data["rates"]

        # Get Bitcoin rate in USD from CoinGecko
        btc_data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd").json()
        btc_rate = btc_data["bitcoin"]["usd"]

        # Get Gold rate in USD per ounce from Yahoo Finance
        gold = yf.Ticker("GC=F")
        gold_price = gold.info['regularMarketPrice']
        gold_rate = gold_price

        # Save to cache in memory
        cached_rates = (rates, btc_rate, gold_rate)
        last_fetch_time = time.time()

        # Save to local JSON file for offline fallback
        with open(CACHE_FILE, "w") as f:
            json.dump({
                "timestamp": last_fetch_time,
                "rates": rates,
                "btc": btc_rate,
                "gold": gold_rate
            }, f)

        return cached_rates

    except Exception as e:
        # If online fetch fails, try to load from cache file
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                cached_rates = (data["rates"], data["btc"], data["gold"])
                messagebox.showwarning("Offline Mode", "Using cached exchange rates.")
                return cached_rates
        else:
            messagebox.showerror("Rate Error", f"Could not get exchange rates:\n{e}")
            return None, None, None

# Function to clear cached data from both memory and file
def clear_cache():
    global cached_rates, last_fetch_time
    cached_rates = None
    last_fetch_time = 0
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    messagebox.showinfo("Cache Cleared", "Rate cache has been cleared.")

# Function to convert currency values
def convert():
    try:
        amount = float(entry_amount.get())  # Ensure valid numeric input
        from_curr = combo_from.get()
        to_curr = combo_to.get()

        # Fetch latest rates
        rates, btc_rate, gold_rate = get_rates()
        if rates is None:
            return

        # Convert from source to USD
        if from_curr == "USD":
            usd = amount
        elif from_curr == "Bitcoin":
            usd = amount * btc_rate
        elif from_curr == "XAU (Gold/Oz)":
            usd = amount * gold_rate
        else:
            usd = amount / rates[from_curr]

        # Convert from USD to target
        if to_curr == "USD":
            result = usd
        elif to_curr == "Bitcoin":
            result = usd / btc_rate
        elif to_curr == "XAU (Gold/Oz)":
            result = usd / gold_rate
        else:
            result = usd * rates[to_curr]

        # Display result
        label_result.config(text=f"{round(result, 2)} {to_curr}")
        update_history_table(from_curr, to_curr)

    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid number.")
    except Exception as e:
        messagebox.showerror("Conversion Error", str(e))

# Swap from/to currencies
def swap_currencies():
    from_curr = combo_from.get()
    to_curr = combo_to.get()
    combo_from.set(to_curr)
    combo_to.set(from_curr)

# Display historical exchange rate chart and table
def update_history_table(from_curr, to_curr):
    try:
        end = datetime.today()
        start = end - timedelta(days=30)

        # Map currencies to yfinance ticker symbols
        def ticker_code(curr):
            if curr == "XAU (Gold/Oz)":
                return "GC=F"
            elif curr == "Bitcoin":
                return "BTC-USD"
            elif curr == "USD":
                return None
            else:
                return f"{curr}=X"

        t1 = ticker_code(from_curr)
        t2 = ticker_code(to_curr)

        # Fetch historical price data
        if t1 and t2:
            df1 = yf.Ticker(t1).history(start=start, end=end)["Close"]
            df2 = yf.Ticker(t2).history(start=start, end=end)["Close"]
            df = pd.DataFrame({from_curr: df1, to_curr: df2}).dropna()
            df = df.reset_index()
            df["Rate"] = df[to_curr] / df[from_curr]
        elif not t1:
            df2 = yf.Ticker(t2).history(start=start, end=end)["Close"]
            df = pd.DataFrame({"Date": df2.index, to_curr: df2.values})
            df["Rate"] = df[to_curr]
        elif not t2:
            df1 = yf.Ticker(t1).history(start=start, end=end)["Close"]
            df = pd.DataFrame({"Date": df1.index, from_curr: df1.values})
            df["Rate"] = 1 / df[from_curr]
        else:
            return

        df = df.sort_values("Date", ascending=False)

        # Clear previous graph/table
        for widget in frame_table.winfo_children():
            widget.destroy()

        # If no data, show a message
        if df.empty:
            tk.Label(frame_table, text="No Historical Data", font=("Helvetica", 12, "italic")).pack()
            return

        # Build the table
        tree = ttk.Treeview(frame_table, columns=("Date", "Rate"), show="headings", height=10)
        tree.heading("Date", text="Date", anchor="center")
        tree.heading("Rate", text=f"{from_curr} to {to_curr}", anchor="center")
        tree.column("Date", anchor="center", width=100)
        tree.column("Rate", anchor="center", width=150)
        for _, row in df.iterrows():
            tree.insert("", "end", values=(row["Date"].strftime("%Y-%m-%d"), round(row["Rate"], 4)))
        tree.pack(fill="both", expand=True)

        # Draw the chart
        fig, ax = plt.subplots(figsize=(4.5, 2.2))
        df_sorted = df.sort_values("Date")
        ax.plot(df_sorted["Date"], df_sorted["Rate"], marker='o')
        ax.set_title(f"{from_curr} to {to_curr} - 30 Day Trend")
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout()

        # Display the chart in GUI
        canvas = FigureCanvasTkAgg(fig, master=frame_table)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    except Exception:
        for widget in frame_table.winfo_children():
            widget.destroy()
        tk.Label(frame_table, text="No Historical Data", font=("Helvetica", 12, "italic")).pack()

# === GUI Setup ===

# Create main window
root = tk.Tk()
root.title("Python Currency Converter")
root.geometry("660x760")
root.resizable(False, False)

# App title
tk.Label(root, text="Python Currency Converter", font=("Helvetica", 18, "bold")).pack(pady=10)

# Input field for amount
tk.Label(root, text="Enter Amount:", font=("Helvetica", 12)).pack()
entry_amount = ttk.Entry(root, font=("Helvetica", 12))
entry_amount.pack(pady=5)

# From currency dropdown
tk.Label(root, text="From Currency:", font=("Helvetica", 12)).pack()
combo_from = ttk.Combobox(root, values=CURRENCIES, state="readonly", font=("Helvetica", 12), width=20)
combo_from.current(0)
combo_from.pack(pady=5)

# To currency dropdown
tk.Label(root, text="To Currency:", font=("Helvetica", 12)).pack()
combo_to = ttk.Combobox(root, values=CURRENCIES, state="readonly", font=("Helvetica", 12), width=20)
combo_to.current(1)
combo_to.pack(pady=5)

# Buttons for swap, convert, and clear cache
btn_frame = tk.Frame(root)
btn_frame.pack(pady=5)
ttk.Button(btn_frame, text="Swap", command=swap_currencies).grid(row=0, column=0, padx=10)
ttk.Button(btn_frame, text="Convert", command=convert).grid(row=0, column=1, padx=10)
ttk.Button(btn_frame, text="Clear Cache", command=clear_cache).grid(row=0, column=2, padx=10)

# Output label for conversion result
label_result = tk.Label(root, text="", font=("Helvetica", 14, "bold"), fg="blue")
label_result.pack(pady=10)

# Section to hold historical data output
tk.Label(root, text="Exchange Rate History (last 30 days)", font=("Helvetica", 12, "bold")).pack(pady=5)
frame_table = tk.Frame(root)
frame_table.pack(pady=10, fill="both", expand=True)

# Footer notes
tk.Label(root, text="Note: Bitcoin = USD/BTC", font=("Helvetica", 8)).pack(pady=5)
tk.Label(root, text="Data from ExchangeRate, CoinGecko & Yahoo Finance", font=("Helvetica", 8)).pack(side="bottom", pady=5)

# Run the app
root.mainloop()