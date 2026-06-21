# scraper.py
# Scraper module to download and parse stats tables from Hockey Reference

import os
import re
from io import StringIO
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
import time

def extract_player_ids(table_html):
    """
    Parses player HTML elements in a table to extract their unique Hockey Reference player ID.
    E.g. '/players/m/mccanja01.html' -> 'mccanja01'
    """
    soup = BeautifulSoup(table_html, 'html.parser')
    player_ids = {}
    
    for row in soup.find_all('tr'):
        # Player cell is usually th or td with data-stat="player"
        player_cell = row.find(attrs={"data-stat": "player"})
        if not player_cell:
            # Fallback to scanning all cells for a link to /players/
            for cell in row.find_all(['th', 'td']):
                a_tag = cell.find('a')
                if a_tag and a_tag.get('href') and '/players/' in a_tag.get('href'):
                    player_cell = cell
                    break
        
        if player_cell:
            player_name = player_cell.text.strip()
            # Try to get data-append-csv attribute first
            player_id = player_cell.get('data-append-csv')
            
            # If not present, parse the link href
            if not player_id:
                a_tag = player_cell.find('a')
                if a_tag and a_tag.get('href'):
                    href = a_tag.get('href')
                    match = re.search(r'/([^/]+)\.s?html?$', href)
                    if match:
                        player_id = match.group(1)
            
            if player_name and player_id:
                # Store the mapping
                player_ids[player_name] = player_id
                
    return player_ids

def find_and_parse_tables(soup, url, output_dir):
    """
    Finds tables in the parsed HTML, prioritizing pre-formatted CSV data,
    falls back to parsing HTML tables, and injects unique player IDs.
    """
    all_tables = []
    
    # 1. Find all table elements to identify their IDs
    for table in soup.find_all('table'):
        table_id = table.get('id')
        if table_id:
            all_tables.append({'id': table_id, 'html': str(table)})
    
    # 2. Also look for tables in comments
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')
        for table in comment_soup.find_all('table'):
            table_id = table.get('id')
            if table_id and not any(t['id'] == table_id for t in all_tables):
                 all_tables.append({'id': table_id, 'html': str(table)})

    if not all_tables:
        print("❌ No tables were found on the page to download.")
        return 0

    files_saved = 0

    for table_info in all_tables:
        table_id = table_info['id']
        if table_id not in ['player_stats', 'goalie_stats']:
            continue  # Skip tables we're not interested in
            
        table_html = table_info['html']
        df = None
        
        try:
            # --- NEW: Extract player IDs from the HTML table ---
            player_ids = extract_player_ids(table_html)
            
            # --- Prioritize finding the pre-formatted CSV data ---
            csv_div_id = f"csv_{table_id}"
            csv_element = soup.find('div', id=csv_div_id)
            
            if csv_element and csv_element.string:
                csv_comment = csv_element.find(string=lambda text: isinstance(text, Comment))
                if csv_comment:
                    df = pd.read_csv(StringIO(csv_comment))

            # --- Fallback to original HTML table parsing if CSV not found ---
            if df is None:
                data_frames = pd.read_html(StringIO(table_html))
                if data_frames:
                    df = data_frames[0]

            if df is not None:
                # Clean up multi-index column headers
                if isinstance(df.columns, pd.MultiIndex):
                    new_columns = []
                    for col in df.columns:
                        if 'Unnamed' in col[0]:
                            new_columns.append(col[1])
                        else:
                            new_columns.append(f"{col[0]}_{col[1]}".strip())
                    df.columns = new_columns

                # Remove header rows that get included in the data
                if 'Rk' in df.columns:
                    df = df[df['Rk'] != 'Rk'].reset_index(drop=True)

                # Remove "Team Totals" rows before saving
                if 'Player' in df.columns:
                    df = df[~df['Player'].str.startswith('Team Totals')].reset_index(drop=True)

                # Inject player ID url column
                if 'Player' in df.columns:
                    df['url'] = df['Player'].map(player_ids).fillna('')

                # Save to file
                match = re.search(r'/(teams/\w+/\d{4})\.html', url)
                if match:
                    filename = os.path.join(output_dir, f"{match.group(1)}_{table_id}.csv")
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                else:
                    filename = os.path.join(output_dir, f"data_{table_id}.csv")
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    f.write(f"# Data downloaded from: {url}\n")
                    df.to_csv(f, index=False)
                    
                print(f"✅ Successfully saved table '{table_id}' to {filename}")
                files_saved += 1
        
        except Exception as e:
            print(f"⚠️ Could not parse or save table '{table_id}': {e}")
            continue
            
    return files_saved

def download_hockey_reference_tables(url, output_base_dir):
    """
    Downloads hockey reference stats tables for a given URL and saves them as CSV files.
    """
    print(f"🚀 Downloading: {url}")
    time.sleep(3.1)  # Respect rate limits of 20 requests per minute
    try:
        # Use headers to avoid blockages
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching URL: {e}")
        return False

    soup = BeautifulSoup(response.content, 'html.parser')
    files_saved = find_and_parse_tables(soup, url, output_base_dir)

    if files_saved > 0:
        print(f"✨ Saved {files_saved} CSV file(s).")
        return True
    else:
        print("No files were saved.")
        return False
