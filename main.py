import argparse
import glob
import os
import re
from io import StringIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import kaleido
import requests
from bs4 import BeautifulSoup, Comment

# Suppress chained assignment warning
pd.options.mode.chained_assignment = None

# --- Constants ---
DEFAULT_COLOR_1 = "#90D3D3"
DEFAULT_COLOR_2 = "#49747B"
DEFAULT_COLOR_3 = "#031623"
RED_RGB = "rgb(228,24,46)"

STAT_NAMES_SKATERS = {
    "GP": "Games Played",
    "Scoring_G": "Goals Scored",
    "Scoring_A": "Assists",
    "Scoring_PTS": "Points Scored",
    "PIM": "Penalty Minutes",
    "Goals_EVG": "Even-Strength Goals",
    "Goals_PPG": "Powerplay Goals",
    "Goals_SHG": "Short-handed Goals",
    "Goals_GWG": "Game-Winnning Goals",
    "Assists_EV": "Even-Strength Assists",
    "Assists_PP": "Powerplay Assists",
    "PPP": "Powerplay Points",
    "Assists_SH": "Short-handed Assists",
    "Shots_SOG": "Shots On Goal",
    "BLK": "Blocked Shots",
    "HIT": "Hits",
    "PM": "Plus/Minus",
}

STAT_NAMES_GOALIES = {
    "GP": "Games Played",
    "GS": "Games Started",
    "W": "Wins",
    "L": "Losses",
    "GA": "Goals Against",
    "Shots": "Shots Against",
    "SV": "Saves",
    "SO": "Shutouts",
    "QS": "Quality Starts",
    "GPS": "Goalie Point Shares",
}

def find_and_parse_tables(soup, url, output_dir, target_table_id):
    """
    Finds tables in the parsed HTML, prioritizing pre-formatted CSV data in hidden divs,
    and falls back to parsing HTML tables.
    """
    all_tables = []
    # Find all table elements to identify their IDs
    for table in soup.find_all('table'):
        table_id = table.get('id')
        if table_id:
            all_tables.append({'id': table_id, 'html': str(table)})
    
    # Also look for tables in comments
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')
        for table in comment_soup.find_all('table'):
            table_id = table.get('id')
            if table_id and not any(t['id'] == table_id for t in all_tables):
                 all_tables.append({'id': table_id, 'html': str(table)})

    if not all_tables:
        print("❌ No tables were found on the page to download.")
        return None, 0

    target_df = None
    files_saved = 0

    for table_info in all_tables:
        table_id = table_info['id']
        if table_id not in ['player_stats', 'goalie_stats']:
            continue  # Skip tables we're not interested in
        df = None
        
        try:
            # --- NEW: Prioritize finding the pre-formatted CSV data ---
            csv_div_id = f"csv_{table_id}"
            csv_element = soup.find('div', id=csv_div_id)
            
            if csv_element and csv_element.string:
                # print(f"✅ Found pre-formatted CSV for table '{table_id}'. Parsing directly.")
                # The actual CSV data is inside a comment within the div
                csv_comment = csv_element.find(string=lambda text: isinstance(text, Comment))
                if csv_comment:
                    df = pd.read_csv(StringIO(csv_comment))

            # --- Fallback to original HTML table parsing if CSV not found ---
            if df is None:
                # print(f"⚠️ No pre-formatted CSV found for '{table_id}'. Parsing HTML table as fallback.")
                table_html = table_info['html']
                data_frames = pd.read_html(StringIO(table_html))
                if data_frames:
                    df = data_frames[0]

            if df is not None:
                # Clean up multi-index column headers
                if isinstance(df.columns, pd.MultiIndex):
                    new_columns = []
                    for col in df.columns:
                        # If the top level is 'Unnamed', just use the bottom level.
                        if 'Unnamed' in col[0]:
                            new_columns.append(col[1])
                        else:
                            # Otherwise, combine them.
                            new_columns.append(f"{col[0]}_{col[1]}".strip())
                    df.columns = new_columns

                # Remove header rows that get included in the data
                if 'Rk' in df.columns:
                    df = df[df['Rk'] != 'Rk'].reset_index(drop=True)

                # Remove "Team Totals" rows before saving
                if 'Player' in df.columns:
                    df = df[~df['Player'].str.startswith('Team Totals')].reset_index(drop=True)
                
                if '+/-' in df.columns:
                    df = df.rename(columns={'+/-': 'PM'})

                # Save to file
                match = re.search(r'/(teams/\w+/\d{4})\.html', url)
                if match:
                    # Create a path like 'teams/SEA/2025_skaters.csv'
                    filename = os.path.join(output_dir, f"{match.group(1)}_{table_id}.csv")
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                else:
                    filename = os.path.join(output_dir, f"data_{table_id}.csv")
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    f.write(f"# Data downloaded from: {url}\n")
                    df.to_csv(f, index=False)
                # print(f"✅ Successfully saved table '{table_id}' to ./{filename}")
                files_saved += 1

                if table_id == target_table_id:
                    target_df = df
        
        except Exception as e:
            print(f"⚠️ Could not parse or save table '{table_id}': {e}")
            continue
            
    return target_df, files_saved

def download_hockey_reference_tables(url, output_base_dir, target_table_id='skaters'):
    print(f"🚀 Downloading: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching URL: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    target_df, files_saved = find_and_parse_tables(soup, url, output_base_dir, target_table_id)

    if files_saved > 0:
        print(f"✨ Saved {files_saved} CSV file(s).")
    else:
        print("No files were saved.")

    return target_df

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return [int(hex_str[i:i+2], 16) for i in (0, 2, 4)]

def get_color_spectrum(n, colors, number_bands=15):
    c1, c2, c3 = colors
    if number_bands <= 1:
        return f"rgb({c1[0]},{c1[1]},{c1[2]})"

    t = n / (number_bands - 1)
    
    if t < 0.5:
        # Interpolate c1 -> c2
        local_t = t * 2
        r = int(c1[0] + local_t * (c2[0] - c1[0]))
        g = int(c1[1] + local_t * (c2[1] - c1[1]))
        b = int(c1[2] + local_t * (c2[2] - c1[2]))
    else:
        # Interpolate c2 -> c3
        local_t = (t - 0.5) * 2
        r = int(c2[0] + local_t * (c3[0] - c2[0]))
        g = int(c2[1] + local_t * (c3[1] - c2[1]))
        b = int(c2[2] + local_t * (c3[2] - c2[2]))

    return f"rgb({r},{g},{b})"

def convert_to_minutes(time_value):
    """Converts a string in the format 'min:sec' to minutes (float)."""
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
    numeric_df = df.select_dtypes(include='number')
    row_sums = numeric_df.sum(axis=0)
    return row_sums.to_frame().T

def get_stat(df, p, s, stat):
    try:
        val = df[(df.Player == p) & (df.Season == s)][stat].values[0]
        return val
    except (IndexError, KeyError):
        return 0

def plot_all_time_leaders(df, stat, stat_name, num, single_season_record, team_name, team_short, seasons, output_dir, team_colors, is_goalie=False):
    # Filter for totals and sort
    top_leaders = df.loc[df.Season == "Total"].sort_values(stat, ascending=False).iloc[:num]
    top_leaders = top_leaders[['Player', 'PlayerAndFlag', stat]].reset_index(drop=True)

    fig = go.Figure()
    names = top_leaders['PlayerAndFlag'].tolist()
    number_seasons = len(seasons)

    for n, s in enumerate(seasons):
        stats = [get_stat(df, p, s, stat) for p in top_leaders.Player]
        
        if s != 'Total':
            colors = [RED_RGB if st == single_season_record else get_color_spectrum(n, team_colors, number_seasons) for st in stats]
            
            trace_kwargs = {
                'name': s,
                'x': names,
                'y': stats,
                'marker_color': colors,
                'showlegend': False
            }

            if stat == "P_M": # Plus Minus special handling
                trace_kwargs.update({
                    'offsetgroup': 0,
                    'width': 0.3,
                    'offset': 0.3 * (n - 1)
                })
            
            fig.add_trace(go.Bar(**trace_kwargs))

        # Add legend entry for the season
        fig.add_trace(go.Bar(x=[None], y=[None],
                             name=s,
                             marker_color=get_color_spectrum(n, team_colors, number_seasons), 
                             showlegend=True))

    if stat == "P_M":
        fig.update_layout(barmode='overlay')
    else:
        fig.update_layout(barmode='group')
    
    # Add legend entry for Single Season Record
    fig.add_trace(go.Bar(x=[None], y=[None],
                         name='Single Season Record',
                         marker_color=RED_RGB,
                         showlegend=True))

    fig.update_layout(barmode='stack')
    fig.update_xaxes(tickangle=45)
    fig.update_layout(title_text=f"{team_name} All-Time Leaders in {stat_name}")

    # Save outputs
    filename = f"top_{'goalies' if is_goalie else 'leaders'}_{stat}_stacked"
    
    png_dir = os.path.join(output_dir, team_short, "png")
    html_dir = os.path.join(output_dir, team_short, "html")
    os.makedirs(png_dir, exist_ok=True)
    os.makedirs(html_dir, exist_ok=True)

    try:
        fig.write_image(os.path.join(png_dir, f"{filename}.png"), scale=2)
        fig.write_html(os.path.join(html_dir, f"{filename}.html"))
        print(f"Generated chart for {stat_name}")
    except Exception as e:
        print(f"Failed to save chart for {stat_name}: {e}")

def load_flags(flags_path):
    if not os.path.exists(flags_path):
        print(f"⚠️ Flags file not found at {flags_path}. Flags will be missing.")
        return pd.DataFrame(columns=["Player", "Flag"])
    try:
        return pd.read_csv(flags_path, header=0, encoding="utf-8-sig", engine="python")
    except Exception as e:
        print(f"⚠️ Error loading flags: {e}")
        return pd.DataFrame(columns=["Player", "Flag"])

def process_stats(team_short, table_type, flags_df, data_dir):
    """
    Loads, concatenates, and calculates career totals for skaters or goalies.
    """
    pattern = os.path.join(data_dir, "teams", team_short, f"*_{table_type}.csv")
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"No files found for {table_type} in {pattern}")
        return None, []

    data = []
    seasons = []
    for f in files:
        season_str = Path(f).stem.split('_')[0]
        seasons.append(season_str)
        print(f"Loading {f}...")
        # Skip Rk and ATOI if present to avoid issues, though ATOI is recalculated later
        df = pd.read_csv(f, header=0, skiprows=1, usecols=lambda x: x != 'Rk')
        data.append(df.assign(Season=season_str))
    
    stacked_df = pd.concat(data).reset_index(drop=True)

    # Specific conversions
    if "Ice Time_TOI" in stacked_df.columns:
        stacked_df['Ice Time_TOI'] = stacked_df["Ice Time_TOI"].apply(convert_to_minutes)
    
    if table_type == 'skaters':
        if "Goals_PPG" in stacked_df.columns and "Assists_PP" in stacked_df.columns:
            stacked_df["PPP"] = stacked_df["Goals_PPG"] + stacked_df["Assists_PP"]

    # Calculate Totals
    list_players = stacked_df.Player.unique().tolist()
    total_rows = []

    for p in list_players:
        player_df = stacked_df[stacked_df.Player == p]
        
        if len(player_df) == 1:
            total_row = player_df.copy()
            total_row["Season"] = "Total"
            total_row["Age"] = 1 
        else:
            total_row = sum_numeric_rows(player_df)
            total_row["Player"] = p
            total_row["Season"] = "Total"
            # Take the last recorded age
            total_row["Age"] = player_df.iloc[-1]["Age"] if "Age" in player_df.columns else 0
            
            # Copy static fields from the first record
            for col in ["Pos", "url"]:
                if col in player_df.columns:
                    total_row[col] = player_df.iloc[0][col]

            # Recalculate percentages/averages
            if table_type == 'skaters':
                if "Ice Time_TOI" in total_row.columns and "GP" in total_row.columns:
                    total_row["ATOI"] = total_row["Ice Time_TOI"] / total_row["GP"]
            elif table_type == 'goalies':
                 if "Goalie Stats_GA" in total_row.columns and "Goalie Stats_Shots" in total_row.columns:
                    ga = total_row["Goalie Stats_GA"].iloc[0]
                    shots = total_row["Goalie Stats_Shots"].iloc[0]
                    sv = total_row["Goalie Stats_SV"].iloc[0] if "Goalie Stats_SV" in total_row.columns else 0
                    if ga == 0:
                        total_row["SV%"] = 100.
                    elif shots > 0:
                        total_row["SV%"] = (sv / shots) * 100

        # Add Flag
        flag_match = flags_df[flags_df.Player == p]
        if not flag_match.empty:
            total_row["Flag"] = flag_match.iloc[0]["Flag"]
        else:
            total_row["Flag"] = "" 

        total_rows.append(total_row)

    if total_rows:
        stacked_df = pd.concat([stacked_df] + total_rows, sort=True).reset_index(drop=True)

    # Create Display Name
    stacked_df["Flag"] = stacked_df["Flag"].fillna("")
    stacked_df["PlayerAndFlag"] = stacked_df["Player"] + stacked_df["Flag"]

    return stacked_df, seasons

def main():
    parser = argparse.ArgumentParser(description="Generate NHL Team Charts")
    parser.add_argument("--team", type=str, default="SEA", help="Team short code (e.g., SEA, TOR)")
    parser.add_argument("--name", type=str, default="Seattle Kraken", help="Full team name")
    parser.add_argument("--start", type=int, default=2022, help="Start season year")
    parser.add_argument("--end", type=int, default=2026, help="End season year")
    parser.add_argument("--update", action="store_true", help="Download fresh data")
    parser.add_argument("--data_dir", type=str, default="hockey_reference_csvs", help="Directory for CSV data")
    parser.add_argument("--output_dir", type=str, default="output", help="Directory for output charts")
    parser.add_argument("--flags", type=str, default="flags.csv", help="Path to flags CSV")
    parser.add_argument("--color1", type=str, default=DEFAULT_COLOR_1, help="Start color (Hex)")
    parser.add_argument("--color2", type=str, default=DEFAULT_COLOR_2, help="Middle color (Hex)")
    parser.add_argument("--color3", type=str, default=DEFAULT_COLOR_3, help="End color (Hex)")

    args = parser.parse_args()

    team_colors = [hex_to_rgb(c) for c in [args.color1, args.color2, args.color3]]

    # 1. Update Data
    if args.update:
        for season in range(args.start, args.end + 1):
            url = f"https://www.hockey-reference.com/teams/{args.team}/{season}.html"
            download_hockey_reference_tables(url, args.data_dir, target_table_id='skaters')

    # 2. Load Flags
    flags_df = load_flags(args.flags)

    # 3. Process Skaters
    print("Processing Skaters...")
    skaters_df, seasons = process_stats(args.team, "player_stats", flags_df, args.data_dir)
    if skaters_df is not None:
        for stat, stat_name in STAT_NAMES_SKATERS.items():
            if stat in skaters_df.columns:
                # Calculate single season record for this stat
                season_max = skaters_df[skaters_df.Season != 'Total'][stat].max()
                plot_all_time_leaders(skaters_df, stat, stat_name, 15, season_max, args.name, args.team, seasons, args.output_dir, team_colors, is_goalie=False)
            else:
                print(f"Skipping {stat} (not in data)")

    # 4. Process Goalies
    print("Processing Goalies...")
    goalies_df, seasons_g = process_stats(args.team, "goalie_stats", flags_df, args.data_dir)
    if goalies_df is not None:
        for stat, stat_name in STAT_NAMES_GOALIES.items():
            if stat in goalies_df.columns:
                season_max = goalies_df[goalies_df.Season != 'Total'][stat].max()
                plot_all_time_leaders(goalies_df, stat, stat_name, 15, season_max, args.name, args.team, seasons_g, args.output_dir, team_colors, is_goalie=True)
            else:
                print(f"Skipping {stat} (not in data)")

if __name__ == "__main__":
    main()
