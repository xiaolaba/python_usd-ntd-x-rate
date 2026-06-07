## install following library first
## pip install pandas requests beautifulsoup4

## fetch historical USD exchange rate, https://www.x-rates.com/historical/?from=USD&amount=1&date=2026-06-07
## open usd2ntd.csv
## fetch 4 values of USD related if not ready, skip te date if not empty, go to next,
## appends to date for each value,
## save file usd2ntd.csv



import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os

def append_all_rates_from_web(csv_filename):
    # 1. Load the CSV file
    if not os.path.exists(csv_filename):
        print(f"Error: The file '{csv_filename}' was not found.")
        return
        
    # FIX: keep_default_na=False stops pandas from converting "N/A" text into an empty NaN value
    df = pd.read_csv(csv_filename, keep_default_na=False)
    
    # Track down the date column automatically
    actual_date_col = None
    for col in df.columns:
        clean_col = str(col).lower().strip()
        if 'date' in clean_col or 'transaction' in clean_col or 'transection' in clean_col:
            actual_date_col = col
            break
            
    if not actual_date_col:
        print(f"Error: Could not automatically detect a date column.")
        print(f"Your CSV file currently has these columns: {list(df.columns)}")
        return
    else:
        print(f"-> Automatically detected date column: '{actual_date_col}'")
        
    # Map lowercase columns to look for existing target columns safely
    col_mapping = {c.lower().strip(): c for c in df.columns}
    
    actual_usd_ntd = col_mapping.get('usd_to_ntd', 'USD_to_NTD')
    actual_usd_hkd = col_mapping.get('usd_to_hkd', 'USD_to_HKD')
    actual_ntd_usd = col_mapping.get('ntd_to_usd', 'NTD_to_USD')
    actual_hkd_usd = col_mapping.get('hkd_to_usd', 'HKD_to_USD')
    
    target_columns = [actual_usd_ntd, actual_usd_hkd, actual_ntd_usd, actual_hkd_usd]
    
    # Ensure all 4 target columns exist and are treated as string objects
    for target_col in target_columns:
        if target_col not in df.columns:
            df[target_col] = ""
        df[target_col] = df[target_col].astype(str)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # FIX: A row is ONLY considered missing if it is completely blank/empty text.
    # Words like "N/A" are recognized as filled text and skipped.
    missing_mask = pd.Series(False, index=df.index)
    for target_col in target_columns:
        is_missing = df[target_col].isna() | (df[target_col].str.strip() == "") | (df[target_col].str.strip() == "<NA>")
        missing_mask = missing_mask | is_missing
        
    total_to_process = missing_mask.sum()
    
    if total_to_process == 0:
        print("All rows are already fully updated with exchange rates. No updates needed.")
        return

    print(f"Found {total_to_process} rows needing web scraping updates. Starting updates...")
    processed_count = 0

    # 2. Iterate and scrape target rows
    for idx, row in df[missing_mask].iterrows():
        processed_count += 1
        date_str = str(row[actual_date_col]).strip()
        url = f"https://www.x-rates.com/historical/?from=USD&amount=1&date={date_str}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- 1. Scrape USD to NTD & HKD ---
            usd_to_twd_elem = soup.find('a', href=lambda href: href and "from=USD" in href and "to=TWD" in href)
            usd_to_hkd_elem = soup.find('a', href=lambda href: href and "from=USD" in href and "to=HKD" in href)
            
            # --- 2. Scrape Inverse NTD & HKD to USD ---
            twd_to_usd_elem = soup.find('a', href=lambda href: href and "from=TWD" in href and "to=USD" in href)
            hkd_to_usd_elem = soup.find('a', href=lambda href: href and "from=HKD" in href and "to=USD" in href)
            
            # Assign values directly from what was found on the web structure
            df.loc[idx, actual_usd_ntd] = usd_to_twd_elem.text.strip() if usd_to_twd_elem else "N/A"
            df.loc[idx, actual_usd_hkd] = usd_to_hkd_elem.text.strip() if usd_to_hkd_elem else "N/A"
            df.loc[idx, actual_ntd_usd] = twd_to_usd_elem.text.strip() if twd_to_usd_elem else "N/A"
            df.loc[idx, actual_hkd_usd] = hkd_to_usd_elem.text.strip() if hkd_to_usd_elem else "N/A"
                
            print(f"[{processed_count}/{total_to_process}] Scraped {date_str} -> "
                  f"USD_to_NTD: {df.loc[idx, actual_usd_ntd]}, "
                  f"NTD_to_USD: {df.loc[idx, actual_ntd_usd]}")
            
        except Exception as e:
            print(f"[{processed_count}/{total_to_process}] {date_str} -> Failed to scrape data: {e}")
            
        # 1-second delay to respect the server
        #time.sleep(1)
        time.sleep(0.3) # 300ms, actual delay more than this as https send/request flow
        
    # 3. Overwrite the original input CSV file with original headers preserved
    df.to_csv(csv_filename, index=False)
    print(f"\nSuccess! All 4 scraped values directly appended back into '{csv_filename}'")

# Run execution
if __name__ == "__main__":
    target_csv = "usd2ntd.csv"
    append_all_rates_from_web(target_csv)