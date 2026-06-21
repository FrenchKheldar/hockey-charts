# processor.py
# Data processor module to read, clean, compute career totals, and match flags

import glob
import os
from pathlib import Path
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

from config import SKATER_COLUMN_MAP, GOALIE_COLUMN_MAP

def read_stats_csv(filepath):
    """
    Reads a stats CSV, skipping the comment line starting with '#' if present.
    Drops the 'Rk' (Rank) column if present to avoid indexing issues.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        first_line = f.readline()
    
    if first_line.startswith('#'):
        df = pd.read_csv(filepath, skiprows=1)
    else:
        df = pd.read_csv(filepath)
        
    if 'Rk' in df.columns:
        df = df.drop(columns=['Rk'])
        
    return df

def convert_to_minutes(time_value):
    """Converts a string in the format 'min:sec' (or 'min') to minutes (float)."""
    if isinstance(time_value, str):
        if ':' in time_value:
            minutes, seconds = time_value.split(':')
        else:
            minutes = time_value
            seconds = 0
        return float(minutes) + float(seconds) / 60.
    elif isinstance(time_value, (int, float)):
        return float(time_value)
    return 0.0

def sum_numeric_rows(df):
    """Sums the numeric columns of a DataFrame and returns a single-row DataFrame."""
    numeric_df = df.select_dtypes(include='number')
    row_sums = numeric_df.sum(axis=0)
    return row_sums.to_frame().T

def fetch_player_flag(player_name, player_id):
    """
    Fetches the nationality flag emoji for a player from their Hockey Reference profile page.
    Uses the 2-letter country code in the birthplace link.
    """
    if not player_id:
        return ""
    
    print(f"🔍 Fetching flag for new player: {player_name} ({player_id})...")
    time.sleep(3.1)  # Respect rate limits of 20 requests per minute
    url = f"https://www.hockey-reference.com/players/{player_id[0]}/{player_id}.html"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Look for birthplaces.cgi?country=XX link
        birth_link = soup.find('a', href=re.compile(r'birthplaces\.cgi\?country='))
        country_code = None
        if birth_link:
            match = re.search(r'country=(\w+)', birth_link.get('href'))
            if match:
                country_code = match.group(1).lower()
                
        # 2. If not found, look for span.f-i.f-xx flag span
        if not country_code:
            flag_span = soup.find('span', class_=re.compile(r'^f-i\s+f-'))
            if flag_span:
                for cls in flag_span.get('class', []):
                    if cls.startswith('f-') and cls != 'f-i':
                        country_code = cls[2:].lower()
                        break
        
        if country_code:
            # Map 2-letter country code to flag emoji using regional indicator symbols
            emoji = "".join(chr(127397 + ord(c)) for c in country_code.upper())
            print(f" Found flag: {emoji} for country: {country_code.upper()}")
            return emoji
    except Exception as e:
        print(f"⚠️ Failed to fetch flag for player {player_name}: {e}")
    return ""

def load_flags(flags_path):
    """Loads flags.csv and ensures headers/columns exist."""
    if not os.path.exists(flags_path):
        print(f"⚠️ Flags file not found at {flags_path}. A new one will be created.")
        return pd.DataFrame(columns=["Player", "Flag", "url"])
    try:
        df = pd.read_csv(flags_path, header=0, encoding="utf-8-sig", engine="python")
        if "url" not in df.columns:
            df["url"] = ""
        df["url"] = df["url"].fillna("")
        df["Player"] = df["Player"].fillna("")
        df["Flag"] = df["Flag"].fillna("")
        return df
    except Exception as e:
        print(f"⚠️ Error loading flags: {e}")
        return pd.DataFrame(columns=["Player", "Flag", "url"])

def abbreviate_name(name):
    """Abbreviates a player name to initial + last name, e.g. Oliver Bjorkstrand -> O. Bjorkstrand."""
    if not name:
        return ""
    parts = name.strip().split()
    if len(parts) <= 1:
        return name
    first = parts[0]
    initial = first[0] + "."
    last = " ".join(parts[1:])
    return f"{initial} {last}"

def process_stats(team_short, table_type, flags_df, flags_path, data_dir):
    """
    Loads, standardizes, calculates career totals, and matches flags for skaters or goalies.
    Also handles self-growing flag cache updates.
    """
    pattern = os.path.join(data_dir, "teams", team_short, f"*_{table_type}.csv")
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"No files found for {table_type} in {pattern}")
        return None, []

    data = []
    seasons = []
    
    # Load and standardize each season file
    for f in files:
        season_str = Path(f).stem.split('_')[0]
        seasons.append(season_str)
        # print(f"Loading {f}...")
        
        df = read_stats_csv(f)
        
        # Rename columns to standard names
        column_map = SKATER_COLUMN_MAP if table_type == 'player_stats' else GOALIE_COLUMN_MAP
        df = df.rename(columns=column_map)
        
        # Convert times to float minutes
        if "TOI" in df.columns:
            df['TOI'] = df["TOI"].apply(convert_to_minutes)
        if "MIN" in df.columns:
            df['MIN'] = df["MIN"].apply(convert_to_minutes)
            
        data.append(df.assign(Season=season_str))
    
    stacked_df = pd.concat(data).reset_index(drop=True)

    # Skater PPG/PPA sum to PPP
    if table_type == 'player_stats':
        if "PPG" in stacked_df.columns and "PPA" in stacked_df.columns:
            stacked_df["PPP"] = stacked_df["PPG"] + stacked_df["PPA"]

    # Calculate Totals
    list_players = stacked_df.Player.unique().tolist()
    total_rows = []
    
    # Keep track of any new flags we discover to write them once
    new_flags_to_save = []

    for p in list_players:
        player_df = stacked_df[stacked_df.Player == p]
        player_id = player_df["url"].dropna().iloc[0] if "url" in player_df.columns and not player_df["url"].dropna().empty else ""
        
        if len(player_df) == 1:
            total_row = player_df.copy()
            total_row["Season"] = "Total"
            total_row["Age"] = player_df.iloc[0]["Age"] if "Age" in player_df.columns else 0
        else:
            total_row = sum_numeric_rows(player_df)
            total_row["Player"] = p
            total_row["Season"] = "Total"
            total_row["Age"] = player_df.iloc[-1]["Age"] if "Age" in player_df.columns else 0
            
            # Copy static fields
            for col in ["Pos", "url"]:
                if col in player_df.columns:
                    total_row[col] = player_df.iloc[0][col]

            # Recalculate career percentages and averages
            if table_type == 'player_stats':
                if "TOI" in total_row.columns and "GP" in total_row.columns:
                    total_row["ATOI"] = total_row["TOI"] / total_row["GP"]
                if "G" in total_row.columns and "SOG" in total_row.columns:
                    sog = total_row["SOG"].iloc[0]
                    total_row["S%"] = (total_row["G"] / sog * 100) if sog > 0 else 0.0
            elif table_type in ['goalies', 'goalie_stats']:
                if "GA" in total_row.columns and "Shots" in total_row.columns:
                    ga = total_row["GA"].iloc[0]
                    shots = total_row["Shots"].iloc[0]
                    sv = total_row["SV"].iloc[0] if "SV" in total_row.columns else 0
                    total_row["SV%"] = (sv / shots) if shots > 0 else 0.0
                if "GA" in total_row.columns and "MIN" in total_row.columns:
                    ga = total_row["GA"].iloc[0]
                    minutes = total_row["MIN"].iloc[0]
                    total_row["GAA"] = (ga * 60) / minutes if minutes > 0 else 0.0
                if "QS" in total_row.columns and "GS" in total_row.columns:
                    qs = total_row["QS"].iloc[0]
                    gs = total_row["GS"].iloc[0]
                    total_row["QS%"] = qs / gs if gs > 0 else 0.0

        # --- Flag Matching & Self-Growing Cache ---
        flag = ""
        
        # 1. Match by Player ID (url column) first (most robust)
        if player_id:
            match = flags_df[flags_df.url == player_id]
            if not match.empty:
                flag = match.iloc[0]["Flag"]
                
        # 2. Fallback to matching by Player Name
        if not flag:
            match = flags_df[flags_df.Player == p]
            if not match.empty:
                flag = match.iloc[0]["Flag"]
                
        # 3. Fetch from Hockey Reference profile page if still missing
        if not flag and player_id:
            flag = fetch_player_flag(p, player_id)
            if flag:
                new_flags_to_save.append({"Player": p, "Flag": flag, "url": player_id})
                
        total_row["Flag"] = flag
        total_rows.append(total_row)

    # Save new flags to cache if any were found
    if new_flags_to_save:
        new_df = pd.DataFrame(new_flags_to_save)
        flags_df = pd.concat([flags_df, new_df], ignore_index=True).drop_duplicates(subset=["Player", "url"], keep="last")
        flags_df.to_csv(flags_path, index=False, encoding="utf-8-sig")
        print(f"💾 Saved {len(new_flags_to_save)} new flags to cache: {flags_path}")

    # Combine single season rows and total rows
    if total_rows:
        stacked_df = pd.concat([stacked_df] + total_rows, sort=True).reset_index(drop=True)

    # Mark active players (played in the latest season of this dataset)
    latest_season = seasons[-1] if seasons else ""
    active_players = set(stacked_df[stacked_df.Season == latest_season].Player.unique())
    stacked_df["Active"] = stacked_df["Player"].apply(lambda p: 1 if p in active_players else 0)

    # Create Display Name
    stacked_df["Flag"] = stacked_df["Flag"].fillna("")
    stacked_df["PlayerAndFlag"] = stacked_df["Player"] + stacked_df["Flag"].apply(lambda f: f" {f}" if f else "")
    
    # Create Abbreviated Display Name for charts (e.g. O. Bjorkstrand 🇩🇰)
    stacked_df["PlayerAbbrAndFlag"] = stacked_df.apply(
        lambda r: abbreviate_name(r["Player"]) + (f" {r['Flag']}" if r["Flag"] else ""),
        axis=1
    )
    
    # Ensure standard url column is clean
    if "url" in stacked_df.columns:
        stacked_df["url"] = stacked_df["url"].fillna("")

    return stacked_df, seasons
