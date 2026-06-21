# config.py
# Global configuration and team database for NHL charts

# --- Team Profiles Database ---
# Maps team short codes to metadata (full name, start/end years, and official colors for chart gradient)
TEAM_CONFIG = {
    "SEA": {
        "name": "Seattle Kraken",
        "start_year": 2022,
        "end_year": 2026,
        "colors": ["#99D9D9", "#355C6F", "#001628"]  # Ice Blue -> Boundless Blue -> Deep Sea Blue
    },
    "ATL": {
        "name": "Atlanta Thrashers",
        "start_year": 2000,
        "end_year": 2011,
        "colors": ["#85B2D2", "#002F6C", "#041E42"]  # Ice Blue -> Thrashers Blue -> Navy Blue
    },
    "TOR": {
        "name": "Toronto Maple Leafs",
        "start_year": 1918,
        "end_year": 2026,
        "colors": ["#00205B", "#FFFFFF", "#001030"]  # Royal Blue, White, Dark Navy
    },
    "EDM": {
        "name": "Edmonton Oilers",
        "start_year": 1980,
        "end_year": 2026,
        "colors": ["#041E42", "#FF4C00", "#000B1A"]  # Navy Blue, Orange, Dark Navy
    },
    "BOS": {
        "name": "Boston Bruins",
        "start_year": 1925,
        "end_year": 2026,
        "colors": ["#FFB81C", "#111111", "#000000"]  # Gold, Black, Dark Black
    },
    "MTL": {
        "name": "Montreal Canadiens",
        "start_year": 1918,
        "end_year": 2026,
        "colors": ["#AF1E2D", "#192168", "#0B0E2A"]  # Red, Royal Blue, Navy
    }
}

# --- Column Renaming Mappings ---
# Unifies multi-level header suffixes and raw hockey-reference names into clean abbreviations
SKATER_COLUMN_MAP = {
    "Scoring_G": "G",
    "Scoring_A": "A",
    "Scoring_PTS": "PTS",
    "Goals_EVG": "EVG",
    "Goals_PPG": "PPG",
    "Goals_SHG": "SHG",
    "Goals_GWG": "GWG",
    "Assists_EV": "EVA",
    "Assists_PP": "PPA",
    "Assists_SH": "SHA",
    "Shots_SOG": "SOG",
    "+/-": "PM",
    "Ice Time_TOI": "TOI",
    "Ice Time_ATOI": "ATOI",
    # Pass-through for already cleaned or manual files
    "G": "G",
    "A": "A",
    "PTS": "PTS",
    "EVG": "EVG",
    "PPG": "PPG",
    "SHG": "SHG",
    "GWG": "GWG",
    "EVA": "EVA",
    "PPA": "PPA",
    "SHA": "SHA",
    "SOG": "SOG",
    "PM": "PM",
    "P_M": "PM",
    "TOI": "TOI",
    "ATOI": "ATOI"
}

GOALIE_COLUMN_MAP = {
    "Goalie Stats_GP": "GP",
    "Goalie Stats_GS": "GS",
    "Goalie Stats_W": "W",
    "Goalie Stats_L": "L",
    "Goalie Stats_GA": "GA",
    "Goalie Stats_Shots": "Shots",
    "Goalie Stats_SV": "SV",
    "Goalie Stats_SO": "SO",
    "Goalie Stats_QS": "QS",
    "Goalie Stats_GPS": "GPS",
    "Goalie Stats_SV%": "SV%",
    "Goalie Stats_MIN": "MIN",
    "Goalie Stats_GAA": "GAA",
    "Goalie Stats_QS%": "QS%",
    # Pass-through for already cleaned or manual files
    "GP": "GP",
    "GS": "GS",
    "W": "W",
    "L": "L",
    "GA": "GA",
    "Shots": "Shots",
    "SV": "SV",
    "SO": "SO",
    "QS": "QS",
    "GPS": "GPS",
    "SV%": "SV%",
    "MIN": "MIN",
    "GAA": "GAA",
    "QS%": "QS%"
}

# --- Statistical Categories to Chart ---
STAT_NAMES_SKATERS = {
    "GP": "Games Played",
    "G": "Goals Scored",
    "A": "Assists",
    "PTS": "Points Scored",
    "PIM": "Penalty Minutes",
    "EVG": "Even-Strength Goals",
    "PPG": "Powerplay Goals",
    "SHG": "Short-handed Goals",
    "GWG": "Game-Winning Goals",
    "EVA": "Even-Strength Assists",
    "PPA": "Powerplay Assists",
    "PPP": "Powerplay Points",
    "SHA": "Short-handed Assists",
    "SOG": "Shots On Goal",
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
