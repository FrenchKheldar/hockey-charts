# main.py
# Main CLI entry point to orchestrate NHL charting data pipeline

import argparse
import glob
import os
import pandas as pd

from config import TEAM_CONFIG, STAT_NAMES_SKATERS, STAT_NAMES_GOALIES
from scraper import download_hockey_reference_tables
from processor import load_flags, process_stats
from visualizer import hex_to_rgb, plot_all_time_leaders, export_data_to_json

# HTML Web Dashboard Template (Self-contained, loaded dynamically)
# HTML Web Dashboard Template (Self-contained, loaded dynamically)
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hockey Charts - NHL Franchise All-Time Leaders</title>
    
    <!-- Google Fonts: EB Garamond (headings) and Lora (body/table data) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
    
    <!-- Plotly.js via CDN -->
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    
    <!-- Styling: Flat White/Clear Editorial Serif Theme -->
    <style>
        :root {
            --bg-light: #fbfbf9; /* Warm off-white paper background */
            --panel-bg: #ffffff;
            --panel-border: #e2e8f0;
            --text-main: #1e293b; /* Dark charcoal */
            --text-muted: #64748b; /* Medium slate grey */
            --text-highlight: #0f172a;
            --record-red: #ac1d37; /* Vintage dark red for single-season records */
            --active-tab: #f8fafc;
            --row-highlight: #fffbeb; /* Cream/gold background highlight for record holders */
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Lora', Georgia, serif;
            background-color: var(--bg-light);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }

        header {
            padding: 2rem 2rem 1.25rem 2rem;
            text-align: center;
            border-bottom: 1px solid var(--panel-border);
            background: var(--panel-bg);
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.02);
        }

        .header-container {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.35rem;
        }

        h1 {
            font-family: 'EB Garamond', Georgia, serif;
            font-size: 2.75rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--text-main);
        }

        .subtitle {
            font-family: 'EB Garamond', Georgia, serif;
            font-style: italic;
            color: var(--text-muted);
            font-size: 1.15rem;
            font-weight: 400;
        }

        main {
            flex: 1;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 2rem;
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 2rem;
        }

        @media (max-width: 1024px) {
            main {
                grid-template-columns: 1fr;
            }
        }

        .panel {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease;
        }

        .panel:hover {
            border-color: #cbd5e1;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }

        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            height: fit-content;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        label {
            font-family: 'EB Garamond', Georgia, serif;
            font-size: 0.95rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            color: var(--text-muted);
        }

        select {
            background-color: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 6px;
            color: var(--text-main);
            padding: 0.7rem 0.9rem;
            font-family: inherit;
            font-size: 0.95rem;
            outline: none;
            cursor: pointer;
            width: 100%;
            transition: border-color 0.2s ease;
        }

        select:focus {
            border-color: #94a3b8;
        }

        .toggle-switch {
            display: flex;
            background: #f8fafc;
            border: 1px solid var(--panel-border);
            border-radius: 6px;
            padding: 0.2rem;
        }

        .toggle-btn {
            flex: 1;
            border: none;
            background: transparent;
            color: var(--text-muted);
            padding: 0.5rem;
            border-radius: 4px;
            font-family: inherit;
            font-weight: 500;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .toggle-btn.active {
            background: var(--panel-bg);
            color: var(--text-main);
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            font-weight: 600;
            border: 1px solid var(--panel-border);
        }

        .search-container {
            position: relative;
        }

        .search-input {
            width: 100%;
            background-color: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 6px;
            color: var(--text-main);
            padding: 0.7rem 0.9rem;
            font-family: inherit;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.2s ease;
        }

        .search-input:focus {
            border-color: #94a3b8;
        }

        .category-list {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            max-height: 400px;
            overflow-y: auto;
            padding-right: 0.3rem;
        }

        /* Custom Scrollbar for list and page */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: var(--panel-border);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #cbd5e1;
        }

        .category-btn {
            text-align: left;
            padding: 0.6rem 0.8rem;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 6px;
            color: var(--text-muted);
            font-family: inherit;
            font-size: 0.9rem;
            font-weight: 400;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .category-btn:hover {
            color: var(--text-main);
            background: #f8fafc;
        }

        .category-btn.active {
            color: var(--text-main);
            background: #f1f5f9;
            border-color: var(--panel-border);
            font-weight: 600;
        }

        .content-area {
            display: flex;
            flex-direction: column;
            gap: 2rem;
            min-width: 0;
        }

        .chart-card {
            min-height: 500px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        #plotly-chart {
            width: 100%;
            height: 500px;
        }

        .table-card {
            overflow: hidden;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .table-header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--panel-border);
            padding-bottom: 0.75rem;
        }

        .table-title {
            font-family: 'EB Garamond', Georgia, serif;
            font-size: 1.35rem;
            font-weight: 600;
        }

        .table-container {
            overflow-x: auto;
            width: 100%;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.95rem;
        }

        th {
            font-family: 'EB Garamond', Georgia, serif;
            font-weight: 600;
            font-size: 0.95rem;
            color: var(--text-muted);
            padding: 0.75rem 1rem;
            border-bottom: 2px solid var(--panel-border);
            text-transform: none;
        }

        td {
            padding: 0.85rem 1rem;
            border-bottom: 1px solid #f1f5f9;
            color: var(--text-main);
        }

        tr:hover td {
            background: #fafafa;
        }

        tr.highlighted-row td {
            background: var(--row-highlight);
            border-bottom-color: #fde68a;
        }

        .badge-pos {
            background: transparent;
            border: 1px solid var(--panel-border);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: 'EB Garamond', Georgia, serif;
        }

        .stat-value-highlight {
            font-weight: 600;
            color: var(--text-main);
        }

        .stat-record-highlight {
            font-weight: 700;
            color: var(--record-red);
        }

        .active-indicator {
            color: #10b981;
            margin-left: 6px;
            font-size: 0.75rem;
            cursor: help;
        }

        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.8rem;
            border-top: 1px solid var(--panel-border);
            margin-top: 3rem;
            background: var(--panel-bg);
        }

        footer a {
            color: var(--text-main);
            text-decoration: none;
            font-weight: 500;
        }

        footer a:hover {
            text-decoration: underline;
        }

        /* Loading Overlay styling */
        .loading-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 1rem;
            height: 100%;
            color: var(--text-muted);
        }

        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid var(--panel-border);
            border-top-color: var(--text-main);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>

    <header>
        <div class="header-container">
            <h1 id="title-banner">Hockey Charts</h1>
            <div class="subtitle" id="subtitle-banner">All-Time Leaders Interactive Dashboard</div>
        </div>
    </header>

    <main>
        <!-- Sidebar Controls Panel -->
        <div class="sidebar panel">
            <div class="control-group">
                <label for="team-select">Franchise</label>
                <select id="team-select"></select>
            </div>

            <div class="control-group">
                <label>Player Type</label>
                <div class="toggle-switch">
                    <button class="toggle-btn active" id="skaters-toggle">Skaters</button>
                    <button class="toggle-btn" id="goalies-toggle">Goalies</button>
                </div>
            </div>

            <div class="control-group">
                <label for="search-input">Search Player</label>
                <div class="search-container">
                    <input type="text" id="search-input" class="search-input" placeholder="Type a name...">
                </div>
            </div>

            <div class="control-group">
                <label>Statistical Category</label>
                <div class="category-list" id="category-list"></div>
            </div>

            <div style="margin-top: 1rem; font-size: 0.8rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.5rem; border-top: 1px solid var(--panel-border); padding-top: 1rem; font-family: 'Lora', Georgia, serif;">
                <span style="color: #10b981; font-size: 0.95rem; line-height: 1;">●</span>
                <span>Active Franchise Player</span>
            </div>
        </div>

        <!-- Main Chart and Table Content -->
        <div class="content-area">
            <!-- Chart Container -->
            <div class="chart-card panel" id="chart-card">
                <div id="plotly-chart">
                    <div class="loading-container">
                        <div class="spinner"></div>
                        <p>Loading database...</p>
                    </div>
                </div>
            </div>

            <!-- Table Container -->
            <div class="table-card panel" id="table-card" style="display: none;">
                <div class="table-header-row">
                    <div class="table-title" id="table-title">Top 15 Leaders</div>
                </div>
                <div class="table-container">
                    <table id="leaders-table">
                        <thead>
                            <tr id="table-headers"></tr>
                        </thead>
                        <tbody id="table-body"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>

    <footer>
        <p>&copy; 2026 hockey-charts.com. Made with &hearts; for hockey fans.</p>
    </footer>

    <!-- Inject data.js (which defines NHL_DATA variable) -->
    <script src="data.js"></script>

    <!-- App Logic -->
    <script>
        document.addEventListener("DOMContentLoaded", () => {
            // Check if database is loaded
            if (typeof NHL_DATA === "undefined") {
                document.getElementById("plotly-chart").innerHTML = `
                    <div class="loading-container">
                        <p style="color: #e4182e;">❌ Error: Database 'data.js' not found.</p>
                        <p style="font-size: 0.85rem; max-width: 400px; text-align: center; margin-top: 0.5rem;">
                            Please make sure you have generated the database by running 
                            <code>python main.py --dashboard</code> in your terminal.
                        </p>
                    </div>`;
                return;
            }

            // State management
            let currentTeam = "";
            let currentPlayerType = "skaters"; // "skaters" or "goalies"
            let currentStat = "";
            
            // Constants mapping clean stat codes to descriptions
            const SKATER_STATS = {
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
                "PM": "Plus/Minus"
            };

            const GOALIE_STATS = {
                "GP": "Games Played",
                "GS": "Games Started",
                "W": "Wins",
                "L": "Losses",
                "GA": "Goals Against",
                "Shots": "Shots Against",
                "SV": "Saves",
                "SO": "Shutouts",
                "QS": "Quality Starts",
                "GPS": "Goalie Point Shares"
            };

            // DOM Elements
            const teamSelect = document.getElementById("team-select");
            const skatersToggle = document.getElementById("skaters-toggle");
            const goaliesToggle = document.getElementById("goalies-toggle");
            const searchInput = document.getElementById("search-input");
            const categoryList = document.getElementById("category-list");
            const tableCard = document.getElementById("table-card");
            const tableHeaders = document.getElementById("table-headers");
            const tableBody = document.getElementById("table-body");
            const tableTitle = document.getElementById("table-title");

            // Initialize dropdown
            const teamCodes = Object.keys(NHL_DATA);
            if (teamCodes.length === 0) {
                document.getElementById("plotly-chart").innerHTML = `
                    <div class="loading-container">
                        <p style="color: #e4182e;">❌ Error: Database is empty.</p>
                    </div>`;
                return;
            }
            
            teamCodes.forEach(code => {
                const opt = document.createElement("option");
                opt.value = code;
                opt.textContent = `${NHL_DATA[code].name} (${code})`;
                teamSelect.appendChild(opt);
            });

            // Set default team
            currentTeam = teamSelect.value;
            
            // Render UI
            updateCategoryList();
            renderDashboard();

            // Event Listeners
            teamSelect.addEventListener("change", (e) => {
                currentTeam = e.target.value;
                updateCategoryList();
                renderDashboard();
            });

            skatersToggle.addEventListener("click", () => {
                if (currentPlayerType !== "skaters") {
                    currentPlayerType = "skaters";
                    skatersToggle.classList.add("active");
                    goaliesToggle.classList.remove("active");
                    updateCategoryList();
                    renderDashboard();
                }
            });

            goaliesToggle.addEventListener("click", () => {
                if (currentPlayerType !== "goalies") {
                    currentPlayerType = "goalies";
                    goaliesToggle.classList.add("active");
                    skatersToggle.classList.remove("active");
                    updateCategoryList();
                    renderDashboard();
                }
            });

            searchInput.addEventListener("input", () => {
                renderDashboard();
            });

            function updateCategoryList() {
                categoryList.innerHTML = "";
                const stats = currentPlayerType === "skaters" ? SKATER_STATS : GOALIE_STATS;
                const statsList = Object.keys(stats);
                
                // Set default stat to first in list
                if (!statsList.includes(currentStat)) {
                    currentStat = statsList[0];
                }
                
                statsList.forEach(key => {
                    const btn = document.createElement("button");
                    btn.className = `category-btn ${key === currentStat ? 'active' : ''}`;
                    btn.innerHTML = `<span>${stats[key]}</span> <span style="font-size: 0.75rem; opacity: 0.6;">${key}</span>`;
                    btn.addEventListener("click", () => {
                        currentStat = key;
                        document.querySelectorAll(".category-btn").forEach(b => b.classList.remove("active"));
                        btn.classList.add("active");
                        renderDashboard();
                    });
                    categoryList.appendChild(btn);
                });
            }

            function getRGBGradientColor(index, numSeasons, colorsHex) {
                // Parse 3 Hex colors
                const parseHex = (hex) => {
                    const clean = hex.replace("#", "");
                    return [
                        parseInt(clean.substring(0, 2), 16),
                        parseInt(clean.substring(2, 4), 16),
                        parseInt(clean.substring(4, 6), 16)
                    ];
                };

                const colors = colorsHex.map(parseHex);
                const c1 = colors[0], c2 = colors[1], c3 = colors[2];
                
                if (numSeasons <= 1) return `rgb(${c1[0]}, ${c1[1]}, ${c1[2]})`;
                const t = index / (numSeasons - 1);
                
                let r, g, b;
                if (t < 0.5) {
                    const localT = t * 2;
                    r = Math.round(c1[0] + localT * (c2[0] - c1[0]));
                    g = Math.round(c1[1] + localT * (c2[1] - c1[1]));
                    b = Math.round(c1[2] + localT * (c2[2] - c1[2]));
                } else {
                    const localT = (t - 0.5) * 2;
                    r = Math.round(c2[0] + localT * (c3[0] - c2[0]));
                    g = Math.round(c2[1] + localT * (c3[1] - c2[1]));
                    b = Math.round(c2[2] + localT * (c3[2] - c2[2]));
                }
                return `rgb(${r}, ${g}, ${b})`;
            }

            function renderDashboard() {
                const teamData = NHL_DATA[currentTeam];
                const statsMap = currentPlayerType === "skaters" ? SKATER_STATS : GOALIE_STATS;
                const statLabel = statsMap[currentStat];
                
                // Get structured data split
                const tableSplit = teamData[currentPlayerType];
                if (!tableSplit || !tableSplit.data || tableSplit.data.length === 0) {
                    document.getElementById("plotly-chart").innerHTML = `
                        <div class="loading-container">
                            <p>No data found for this category.</p>
                        </div>`;
                    tableCard.style.display = "none";
                    return;
                }
                
                // Map array of arrays to list of objects
                const columns = tableSplit.columns;
                const rawRows = tableSplit.data.map(row => {
                    const obj = {};
                    columns.forEach((col, idx) => {
                        obj[col] = row[idx];
                    });
                    return obj;
                });
                
                // 1. Find columns index
                const playerCol = "Player";
                const displayCol = "PlayerAndFlag";
                const seasonCol = "Season";
                const ageCol = "Age";
                const posCol = "Pos";
                
                // Check if stat is present
                if (!(currentStat in rawRows[0])) {
                    document.getElementById("plotly-chart").innerHTML = `
                        <div class="loading-container">
                            <p>The statistical category <strong>${statLabel} (${currentStat})</strong> is not present in the dataset.</p>
                        </div>`;
                    tableCard.style.display = "none";
                    return;
                }
                
                // 2. Identify top 15 leaders from "Total" rows
                let totalRows = rawRows.filter(r => r[seasonCol] === "Total");
                
                // Apply player search filter if active
                const query = searchInput.value.trim().toLowerCase();
                if (query) {
                    totalRows = totalRows.filter(r => r[playerCol].toLowerCase().includes(query));
                }
                
                // Sort totals descending
                totalRows.sort((a, b) => b[currentStat] - a[currentStat]);
                
                // Take top 15
                const topLeaders = totalRows.slice(0, 15);
                const topLeaderNames = topLeaders.map(r => r[playerCol]);
                
                if (topLeaders.length === 0) {
                    document.getElementById("plotly-chart").innerHTML = `
                        <div class="loading-container">
                            <p>No players found matching search.</p>
                        </div>`;
                    tableCard.style.display = "none";
                    return;
                }
                
                // 3. Find list of active seasons (excluding "Total" and lockout 2005)
                const seasonSet = new Set(rawRows.map(r => r[seasonCol]).filter(s => s !== "Total" && s !== "2005"));
                const seasonsList = Array.from(seasonSet).sort();
                const numSeasons = seasonsList.length;
                
                // 4. Calculate single season record for highlighting (excluding Total)
                const seasonRowsOnly = rawRows.filter(r => r[seasonCol] !== "Total");
                const singleSeasonRecord = seasonRowsOnly.length > 0 ? Math.max(...seasonRowsOnly.map(r => r[currentStat] || 0)) : 0;
                
                // 5. Build stacked chart data structure
                const traces = [];
                // Use PlayerAbbrAndFlag for x-axis if available, fallback to displayCol. Append green dot if active.
                const abbrCol = "PlayerAbbrAndFlag";
                const xLabels = topLeaders.map(r => {
                    const baseName = r[abbrCol] || r[displayCol];
                    return baseName + (r["Active"] ? ' <span style="color: #10b981;">●</span>' : '');
                });
                const fullNames = topLeaders.map(r => r[displayCol]);
                const redColor = "rgb(228,24,46)"; // Standard record highlight color
                
                // Set hover template based on statistic type
                let hoverTemplateStr = '<b>%{customdata}</b><br>%{data.name}: %{y}<extra></extra>';
                if (currentStat === "SV%") {
                    hoverTemplateStr = '<b>%{customdata}</b><br>%{data.name}: %{y:.3f}<extra></extra>';
                } else if (currentStat === "GAA") {
                    hoverTemplateStr = '<b>%{customdata}</b><br>%{data.name}: %{y:.2f}<extra></extra>';
                }

                // For each season, build a bar trace
                seasonsList.forEach((season, sIdx) => {
                    const yValues = [];
                    const markerColors = [];
                    
                    topLeaders.forEach(leader => {
                        // Find this player's row for this season
                        const sRow = rawRows.find(r => r[playerCol] === leader[playerCol] && r[seasonCol] === season);
                        const val = sRow ? (sRow[currentStat] || 0) : 0;
                        yValues.push(val);
                        
                        // Highlight in Red if it matches the single season record
                        if (val === singleSeasonRecord && singleSeasonRecord > 0) {
                            markerColors.push(redColor);
                        } else {
                            markerColors.push(getRGBGradientColor(sIdx, numSeasons, teamData.colors));
                        }
                    });
                    
                    traces.push({
                        x: xLabels,
                        y: yValues,
                        name: season,
                        type: 'bar',
                        marker: {
                            color: markerColors
                        },
                        customdata: fullNames,
                        hovertemplate: hoverTemplateStr,
                        // Overlap settings for Plus/Minus charting
                        offsetgroup: currentStat === "PM" ? 0 : undefined,
                        width: currentStat === "PM" ? 0.3 : undefined,
                        offset: currentStat === "PM" ? (0.3 * (sIdx - 1)) : undefined
                    });
                });
                
                // Render Chart
                const layout = {
                    barmode: currentStat === "PM" ? 'overlay' : 'stack',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    font: {
                        color: 'var(--text-main)',
                        family: "'Lora', Georgia, serif"
                    },
                    title: {
                        text: `${teamData.name} All-Time Leaders: ${statLabel}`,
                        font: {
                            family: "'EB Garamond', Georgia, serif",
                            size: 22,
                            weight: 600
                        }
                    },
                    margin: { t: 60, b: 80, l: 50, r: 80 },
                    xaxis: {
                        tickangle: 45,
                        gridcolor: 'rgba(0, 0, 0, 0.06)',
                        zeroline: true,
                        zerolinecolor: 'rgba(0, 0, 0, 0.12)'
                    },
                    yaxis: {
                        gridcolor: 'rgba(0, 0, 0, 0.06)',
                        zeroline: true,
                        zerolinecolor: 'rgba(0, 0, 0, 0.12)',
                        title: {
                            text: statLabel,
                            font: { size: 12 }
                        }
                    },
                    showlegend: true,
                    legend: {
                        x: 1,
                        xanchor: 'right',
                        y: 1,
                        bgcolor: 'rgba(255, 255, 255, 0.9)',
                        bordercolor: 'var(--panel-border)',
                        borderwidth: 1
                    }
                };
                
                const config = {
                    responsive: true,
                    displayModeBar: false
                };
                
                document.getElementById('plotly-chart').innerHTML = '';
                Plotly.newPlot('plotly-chart', traces, layout, config);
                
                // 6. Render Data Table
                tableCard.style.display = "block";
                tableTitle.textContent = `All-Time Leaders: ${statLabel} (Top 15)`;
                
                // Define headers
                const showHeaders = ["Rank", "Player", "Pos", "Career GP", statLabel, "Best Season"];
                tableHeaders.innerHTML = showHeaders.map(h => `<th>${h}</th>`).join("");
                
                // Populate rows
                tableBody.innerHTML = "";
                topLeaders.forEach((leader, idx) => {
                    const row = document.createElement("tr");
                    
                    // Highlight rows that have the single-season record in their stack
                    let holdsRecord = false;
                    const leaderSeasonRows = rawRows.filter(r => r[playerCol] === leader[playerCol] && r[seasonCol] !== "Total");
                    leaderSeasonRows.forEach(sr => {
                        if ((sr[currentStat] || 0) === singleSeasonRecord && singleSeasonRecord > 0) {
                            holdsRecord = true;
                        }
                    });
                    
                    if (holdsRecord) {
                        row.className = "highlighted-row";
                    }
                    
                    // Find player career stats
                    const careerGP = leader["GP"] || 0;
                    const val = leader[currentStat];
                    
                    // Format float numbers like GAA and SV%
                    let formattedVal = (val !== null && val !== undefined) ? val : 0;
                    if (typeof formattedVal === "number") {
                        if (currentStat === "SV%") {
                            formattedVal = formattedVal.toFixed(3);
                        } else if (currentStat === "GAA") {
                            formattedVal = formattedVal.toFixed(2);
                        } else if (!Number.isInteger(formattedVal)) {
                            formattedVal = formattedVal.toFixed(1);
                        }
                    }
                    
                    // Find player's best season stat value
                    const bestSeasonVal = leaderSeasonRows.length > 0 ? Math.max(...leaderSeasonRows.map(r => r[currentStat] || 0)) : 0;
                    let bestSeasonFormatted = (bestSeasonVal !== null && bestSeasonVal !== undefined) ? bestSeasonVal : 0;
                    if (typeof bestSeasonFormatted === "number") {
                        if (currentStat === "SV%") {
                            bestSeasonFormatted = bestSeasonFormatted.toFixed(3);
                        } else if (currentStat === "GAA") {
                            bestSeasonFormatted = bestSeasonFormatted.toFixed(2);
                        } else if (!Number.isInteger(bestSeasonFormatted)) {
                            bestSeasonFormatted = bestSeasonFormatted.toFixed(1);
                        }
                    }
                    
                    // Render Row Cells
                    const activeDotHtml = leader["Active"] ? ' <span class="active-indicator" title="Active Franchise Player">●</span>' : '';
                    row.innerHTML = `
                        <td style="font-weight: 600; width: 60px;">#${idx + 1}</td>
                        <td style="font-weight: 500;">
                            ${leader[displayCol]}${activeDotHtml}
                        </td>
                        <td><span class="badge-pos">${leader[posCol] || 'N/A'}</span></td>
                        <td>${careerGP}</td>
                        <td class="stat-value-highlight">${formattedVal}</td>
                        <td class="${holdsRecord ? 'stat-record-highlight' : ''}">${bestSeasonFormatted}</td>
                    `;
                    
                    tableBody.appendChild(row);
                });
            }
        });
    </script>
    <!-- GoatCounter Analytics (Privacy-focused, cookie-less) -->
    <script data-goatcounter="https://frenchkheldar.goatcounter.com/count"
            async src="//gc.zgo.at/count.js"></script>
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(description="NHL Franchise Leaders Charting CLI Tool")
    parser.add_argument("--team", type=str, default=None, help="Team short code (e.g. SEA, ATL, TOR)")
    parser.add_argument("--name", type=str, default=None, help="Full franchise name (overrides config)")
    parser.add_argument("--start", type=int, default=None, help="Start year (overrides config)")
    parser.add_argument("--end", type=int, default=None, help="End year (overrides config)")
    parser.add_argument("--update", action="store_true", help="Scrape fresh data from Hockey Reference")
    parser.add_argument("--data_dir", type=str, default="hockey_reference_csvs", help="Directory for CSV datasets")
    parser.add_argument("--output_dir", type=str, default="output", help="Directory for output charts & web files")
    parser.add_argument("--flags", type=str, default="flags.csv", help="Path to player country flags CSV")
    parser.add_argument("--color1", type=str, default=None, help="Start color hex override")
    parser.add_argument("--color2", type=str, default=None, help="Middle color hex override")
    parser.add_argument("--color3", type=str, default=None, help="End color hex override")
    parser.add_argument("--all", action="store_true", help="Process all franchises defined in the database config")
    parser.add_argument("--dashboard", action="store_true", help="Generate/refresh the interactive web dashboard files")
    parser.add_argument("--skip_charts", action="store_true", help="Skip generating static PNG/HTML charts (for fast website iteration)")

    args = parser.parse_args()

    # 1. Load Flags Database
    flags_path = args.flags
    flags_df = load_flags(flags_path)

    # 2. Determine teams to process
    teams_to_process = []
    if args.all:
        teams_to_process = list(TEAM_CONFIG.keys())
    else:
        # Fall back to SEA if nothing is specified
        team_code = args.team if args.team else "SEA"
        teams_to_process = [team_code]

    # 3. Update/Scrape data if requested (only for specified teams to be fast and safe)
    if args.update:
        print(f"🎬 Updating data for franchises: {', '.join(teams_to_process)}")
        for team_code in teams_to_process:
            team_profile = TEAM_CONFIG.get(team_code, {
                "name": f"{team_code} Franchise",
                "start_year": 2022,
                "end_year": 2026,
                "colors": ["#99D9D9", "#355C6F", "#001628"]
            })
            start_year = args.start if (args.start and not args.all) else team_profile["start_year"]
            end_year = args.end if (args.end and not args.all) else team_profile["end_year"]
            
            print(f"Scraping seasons for {team_code}...")
            for season in range(start_year, end_year + 1):
                if season == 2005:
                    print("🚫 Lockout season 2004-2005 skipped.")
                    continue
                url = f"https://www.hockey-reference.com/teams/{team_code}/{season}.html"
                download_hockey_reference_tables(url, args.data_dir)

    # 4. Compile database for all configured teams that have local CSV files
    consolidated_db = {}
    flags_df = load_flags(flags_path)
    
    print("\n📦 Compiling database and generating charts...")
    for team_code in TEAM_CONFIG.keys():
        # Check if local data exists for this team
        skater_pattern = os.path.join(args.data_dir, "teams", team_code, "*_player_stats.csv")
        goalie_pattern = os.path.join(args.data_dir, "teams", team_code, "*_goalie_stats.csv")
        
        has_skaters = len(glob.glob(skater_pattern)) > 0
        has_goalies = len(glob.glob(goalie_pattern)) > 0
        
        if not (has_skaters or has_goalies):
            continue  # Skip teams with no local datasets
            
        print(f"\n--- 🏒 Processing {team_code} ---")
        team_profile = TEAM_CONFIG[team_code]
        
        # Override default configuration if requested (only when processing a single team)
        team_name = team_profile["name"]
        start_year = team_profile["start_year"]
        end_year = team_profile["end_year"]
        
        if not args.all and team_code == (args.team if args.team else "SEA"):
            team_name = args.name if args.name else team_name
            start_year = args.start if args.start else start_year
            end_year = args.end if args.end else end_year

        colors_hex = team_profile["colors"]
        if not args.all and team_code == (args.team if args.team else "SEA"):
            if args.color1 and args.color2 and args.color3:
                colors_hex = [args.color1, args.color2, args.color3]
        team_colors = [hex_to_rgb(c) for c in colors_hex]

        # Reload flags DataFrame since it grows during processing
        flags_df = load_flags(flags_path)

        # Process Skaters Stats
        print(f"Processing Skaters for {team_code}...")
        skaters_df, seasons = process_stats(team_code, "player_stats", flags_df, flags_path, args.data_dir)
        
        # Re-load flags again for goalies run (just in case new skater flags were added)
        flags_df = load_flags(flags_path)

        # Process Goalies Stats
        print(f"Processing Goalies for {team_code}...")
        goalies_df, seasons_g = process_stats(team_code, "goalie_stats", flags_df, flags_path, args.data_dir)

        # Plot Static Charts
        if not args.skip_charts:
            if skaters_df is not None:
                for stat, stat_name in STAT_NAMES_SKATERS.items():
                    if stat in skaters_df.columns:
                        season_max = skaters_df[skaters_df.Season != 'Total'][stat].max()
                        plot_all_time_leaders(skaters_df, stat, stat_name, 15, season_max, team_name, team_code, seasons, args.output_dir, team_colors, is_goalie=False)

            if goalies_df is not None:
                for stat, stat_name in STAT_NAMES_GOALIES.items():
                    if stat in goalies_df.columns:
                        season_max = goalies_df[goalies_df.Season != 'Total'][stat].max()
                        plot_all_time_leaders(goalies_df, stat, stat_name, 15, season_max, team_name, team_code, seasons_g, args.output_dir, team_colors, is_goalie=True)

        # Package structured team data (replace NaN with None for valid JSON output)
        skaters_split = None
        if skaters_df is not None:
            skaters_clean = skaters_df.where(pd.notnull(skaters_df), None)
            skaters_split = skaters_clean.to_dict(orient="split")
            
        goalies_split = None
        if goalies_df is not None:
            goalies_clean = goalies_df.where(pd.notnull(goalies_df), None)
            goalies_split = goalies_clean.to_dict(orient="split")

        consolidated_db[team_code] = {
            "name": team_name,
            "colors": colors_hex,
            "start_year": start_year,
            "end_year": end_year,
            "skaters": skaters_split,
            "goalies": goalies_split
        }

    # 8. Export JSON and JS databases
    export_data_to_json(consolidated_db, args.output_dir)

    # 9. Generate interactive web dashboard index.html if requested
    if args.dashboard:
        index_path = os.path.join(args.output_dir, "index.html")
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(DASHBOARD_HTML)
        print(f"\n🖥️  Interactive dashboard generated successfully at: {index_path}")
        print("💡 Open this file in your browser to view all-time charts instantly!")

if __name__ == "__main__":
    main()
