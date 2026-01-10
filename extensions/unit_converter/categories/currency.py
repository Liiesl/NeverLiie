import os
import json
import time
import threading
import logging
from datetime import datetime

# Try importing yfinance
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

from .base import BaseCategory

class CurrencyCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.cache_file = None
        self.last_updated_str = "Offline Estimate"
        self.default_targets = ["USD", "EUR", "GBP", "JPY", "BTC"]
        
        # 1. Comprehensive Global Definitions
        # Rough factors (USD Base = 1.0) - yfinance will overwrite these with live data
        self.definitions = {
            # --- Majors & ECB ---
            "USD": {"factor": 1.0, "display_name": "US Dollar", "aliases": ["dollar", "$"]},
            "EUR": {"factor": 1.08, "display_name": "Euro", "aliases": ["euro", "€"]},
            "JPY": {"factor": 0.0067, "display_name": "Japanese Yen", "aliases": ["yen", "¥"]},
            "GBP": {"factor": 1.26, "display_name": "British Pound", "aliases": ["pound", "£"]},
            "CHF": {"factor": 1.12, "display_name": "Swiss Franc", "aliases": ["franc", "chf"]},
            "AUD": {"factor": 0.65, "display_name": "Australian Dollar", "aliases": ["aud"]},
            "CAD": {"factor": 0.74, "display_name": "Canadian Dollar", "aliases": ["cad"]},
            "NZD": {"factor": 0.61, "display_name": "NZ Dollar", "aliases": ["nzd"]},
            
            # --- Americas ---
            "BRL": {"factor": 0.20, "display_name": "Brazilian Real", "aliases": ["brl", "real"]},
            "MXN": {"factor": 0.059, "display_name": "Mexican Peso", "aliases": ["mxn", "peso"]},
            "ARS": {"factor": 0.0011, "display_name": "Argentine Peso", "aliases": ["ars"]},
            "CLP": {"factor": 0.0011, "display_name": "Chilean Peso", "aliases": ["clp"]},
            "COP": {"factor": 0.00025, "display_name": "Colombian Peso", "aliases": ["cop"]},
            "PEN": {"factor": 0.27, "display_name": "Peruvian Sol", "aliases": ["pen"]},
            
            # --- Asia/Pacific ---
            "CNY": {"factor": 0.14, "display_name": "Chinese Yuan", "aliases": ["cny", "yuan"]},
            "HKD": {"factor": 0.13, "display_name": "HK Dollar", "aliases": ["hkd"]},
            "INR": {"factor": 0.012, "display_name": "Indian Rupee", "aliases": ["inr", "rupee", "₹"]},
            "KRW": {"factor": 0.00075, "display_name": "South Korean Won", "aliases": ["krw", "won"]},
            "SGD": {"factor": 0.74, "display_name": "Singapore Dollar", "aliases": ["sgd"]},
            "TWD": {"factor": 0.031, "display_name": "Taiwan Dollar", "aliases": ["twd"]},
            "VND": {"factor": 0.00004, "display_name": "Vietnamese Dong", "aliases": ["vnd"]},
            "THB": {"factor": 0.028, "display_name": "Thai Baht", "aliases": ["thb", "baht"]},
            "MYR": {"factor": 0.21, "display_name": "Malaysian Ringgit", "aliases": ["myr"]},
            "PHP": {"factor": 0.018, "display_name": "Philippine Peso", "aliases": ["php"]},
            "IDR": {"factor": 0.000064, "display_name": "Indonesian Rupiah", "aliases": ["idr"]},
            "PKR": {"factor": 0.0036, "display_name": "Pakistani Rupee", "aliases": ["pkr"]},
            
            # --- Middle East & Africa ---
            "AED": {"factor": 0.27, "display_name": "UAE Dirham", "aliases": ["aed", "dirham"]},
            "SAR": {"factor": 0.27, "display_name": "Saudi Riyal", "aliases": ["sar", "riyal"]},
            "ILS": {"factor": 0.27, "display_name": "Israeli Shekel", "aliases": ["ils", "shekel"]},
            "TRY": {"factor": 0.031, "display_name": "Turkish Lira", "aliases": ["try", "lira"]},
            "ZAR": {"factor": 0.053, "display_name": "South African Rand", "aliases": ["zar", "rand"]},
            "EGP": {"factor": 0.021, "display_name": "Egyptian Pound", "aliases": ["egp"]},
            "KWD": {"factor": 3.25, "display_name": "Kuwaiti Dinar", "aliases": ["kwd"]},
            "QAR": {"factor": 0.27, "display_name": "Qatari Rial", "aliases": ["qar"]},
            "NGN": {"factor": 0.00065, "display_name": "Nigerian Naira", "aliases": ["ngn"]},
            "KES": {"factor": 0.0075, "display_name": "Kenyan Shilling", "aliases": ["kes"]},
            
            # --- Europe (Non-Euro) ---
            "PLN": {"factor": 0.25, "display_name": "Polish Zloty", "aliases": ["pln"]},
            "SEK": {"factor": 0.096, "display_name": "Swedish Krona", "aliases": ["sek"]},
            "NOK": {"factor": 0.095, "display_name": "Norwegian Krone", "aliases": ["nok"]},
            "DKK": {"factor": 0.14, "display_name": "Danish Krone", "aliases": ["dkk"]},
            "CZK": {"factor": 0.043, "display_name": "Czech Koruna", "aliases": ["czk"]},
            "HUF": {"factor": 0.0028, "display_name": "Hungarian Forint", "aliases": ["huf"]},
            "RON": {"factor": 0.22, "display_name": "Romanian Leu", "aliases": ["ron"]},
            
            # --- Crypto & Commodities ---
            "BTC": {"factor": 65000.0, "display_name": "Bitcoin", "aliases": ["bitcoin", "btc"]},
            "ETH": {"factor": 3500.0, "display_name": "Ethereum", "aliases": ["ethereum", "eth"]},
            "SOL": {"factor": 150.0, "display_name": "Solana", "aliases": ["sol"]},
            "XAU": {"factor": 2350.0, "display_name": "Gold (oz)", "aliases": ["gold"]},
            "XAG": {"factor": 28.0, "display_name": "Silver (oz)", "aliases": ["silver"]},
        }
        
        # 2. Comprehensive Ticker Mapping
        self.ticker_map = {
            # Quote: SYM/USD (Factor = Rate)
            "EUR": {"ticker": "EURUSD=X", "invert": False},
            "GBP": {"ticker": "GBPUSD=X", "invert": False},
            "AUD": {"ticker": "AUDUSD=X", "invert": False},
            "NZD": {"ticker": "NZDUSD=X", "invert": False},
            "BTC": {"ticker": "BTC-USD", "invert": False},
            "ETH": {"ticker": "ETH-USD", "invert": False},
            "SOL": {"ticker": "SOL-USD", "invert": False},
            "XAU": {"ticker": "GC=F", "invert": False},  # Gold Futures (USD per oz)
            "XAG": {"ticker": "SI=F", "invert": False},  # Silver Futures (USD per oz)
            
            # Quote: USD/SYM (Factor = 1/Rate)
            "JPY": {"ticker": "USDJPY=X", "invert": True},
            "CHF": {"ticker": "USDCHF=X", "invert": True},
            "CAD": {"ticker": "USDCAD=X", "invert": True},
            "BRL": {"ticker": "USDBRL=X", "invert": True},
            "MXN": {"ticker": "USDMXN=X", "invert": True},
            "ARS": {"ticker": "USDARS=X", "invert": True},
            "CLP": {"ticker": "USDCLP=X", "invert": True},
            "COP": {"ticker": "USDCOP=X", "invert": True},
            "PEN": {"ticker": "USDPEN=X", "invert": True},
            "CNY": {"ticker": "USDCNY=X", "invert": True},
            "HKD": {"ticker": "USDHKD=X", "invert": True},
            "INR": {"ticker": "USDINR=X", "invert": True},
            "KRW": {"ticker": "USDKRW=X", "invert": True},
            "SGD": {"ticker": "USDSGD=X", "invert": True},
            "TWD": {"ticker": "USDTWD=X", "invert": True},
            "VND": {"ticker": "USDVND=X", "invert": True},
            "THB": {"ticker": "USDTHB=X", "invert": True},
            "MYR": {"ticker": "USDMYR=X", "invert": True},
            "PHP": {"ticker": "USDPHP=X", "invert": True},
            "IDR": {"ticker": "USDIDR=X", "invert": True},
            "PKR": {"ticker": "USDPKR=X", "invert": True},
            "AED": {"ticker": "USDAED=X", "invert": True},
            "SAR": {"ticker": "USDSAR=X", "invert": True},
            "ILS": {"ticker": "USDILS=X", "invert": True},
            "TRY": {"ticker": "USDTRY=X", "invert": True},
            "ZAR": {"ticker": "USDZAR=X", "invert": True},
            "EGP": {"ticker": "USDEGP=X", "invert": True},
            "KWD": {"ticker": "USDKWD=X", "invert": True},
            "QAR": {"ticker": "USDQAR=X", "invert": True},
            "NGN": {"ticker": "USDNGN=X", "invert": True},
            "KES": {"ticker": "USDKES=X", "invert": True},
            "PLN": {"ticker": "USDPLN=X", "invert": True},
            "SEK": {"ticker": "USDSEK=X", "invert": True},
            "NOK": {"ticker": "USDNOK=X", "invert": True},
            "DKK": {"ticker": "USDDKK=X", "invert": True},
            "CZK": {"ticker": "USDCZK=X", "invert": True},
            "HUF": {"ticker": "USDHUF=X", "invert": True},
            "RON": {"ticker": "USDRON=X", "invert": True},
        }

        self._build_lookup()

    def set_data_path(self, folder_path):
        """Called by main extension to set storage path."""
        self.cache_file = os.path.join(folder_path, "currency_rates_v2.json")
        
        if HAS_YFINANCE:
            threading.Thread(target=self._update_process, daemon=True).start()

    def get_specific_result(self, val, src_unit_str, target_unit_str):
        """Override to add source info to description."""
        results = super().get_specific_result(val, src_unit_str, target_unit_str)
        if results:
            # Update the description of the result item to show data source
            results[0].description = f"Rate Source: {self.last_updated_str}"
        return results

    def _update_process(self):
        if not self.cache_file: return

        # 1. Try to load existing cache
        if os.path.exists(self.cache_file):
            try:
                mtime = os.path.getmtime(self.cache_file)
                age = time.time() - mtime
                
                # Load the data regardless of age so we have something to show
                with open(self.cache_file, 'r') as f:
                    self._apply_rates(json.load(f), source="Cache")

                # If the cache is fresh (< 24h), we are done!
                if age < 86400:
                    print("[Currency] Cache is fresh.")
                    return
                
                # If the download FAILED less than 1 hour ago, don't try again yet
                # This prevents spamming Yahoo if the user is offline.
                if 0 < (age - 86400) < 3600: 
                    return

            except Exception as e:
                print(f"[Currency] Cache error: {e}")

        # 2. Download (only if cache is old or missing)
        self._download_rates()

    def _download_rates(self):
        print("[Currency] Downloading live rates...")
        try:
            tickers = [t["ticker"] for t in self.ticker_map.values()]
            
            # Download 2 days to ensure we have at least one valid close if yesterday was a holiday
            df = yf.download(tickers, period="5d", progress=False)
            
            if df.empty:
                print("[Currency] Download empty.")
                return

            # Extract just the Close prices
            # yfinance structure varies. Sometimes it's df['Close'], sometimes it's just df.
            if "Close" in df.columns.levels[0] if hasattr(df.columns, 'levels') else "Close" in df:
                data_source = df["Close"]
            else:
                data_source = df

            clean_data = {}
            
            # CRITICAL FIX: Iterate tickers individually to find the last VALID value for each
            # This handles cases where Bitcoin trades on Sunday but Euro doesn't.
            for t in tickers:
                try:
                    if t in data_source.columns:
                        # Get the column, remove empty rows (NaN), take the last one
                        series = data_source[t].dropna()
                        if not series.empty:
                            val = float(series.iloc[-1])
                            clean_data[t] = val
                        else:
                            print(f"[Currency] No valid data found for {t}")
                    else:
                        print(f"[Currency] Column {t} missing from response")
                except Exception as ex:
                    print(f"[Currency] Error extracting {t}: {ex}")

            if clean_data:
                # Save to disk
                os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
                with open(self.cache_file, 'w') as f:
                    json.dump(clean_data, f)
                
                self._apply_rates(clean_data, source="Yahoo Finance (Live)")
                print(f"[Currency] Successfully updated {len(clean_data)} rates.")
            
        except Exception as e:
            print(f"[Currency] Global Download Error: {e}")
            import traceback
            traceback.print_exc()

    def _apply_rates(self, data, source="Unknown"):
        count = 0
        for symbol, info in self.ticker_map.items():
            t = info["ticker"]
            if t in data:
                rate = data[t]
                new_factor = (1.0 / rate) if info["invert"] else rate
                
                # SAFETY FIX: Create entry if it doesn't exist
                if symbol not in self.definitions:
                    self.definitions[symbol] = {
                        "display_name": symbol,
                        "aliases": [symbol.lower()]
                    }
                
                self.definitions[symbol]["factor"] = new_factor
                count += 1
        
        if count > 0:
            dt = datetime.now().strftime("%H:%M")
            self.last_updated_str = f"{source} @ {dt}"
            self._build_lookup()