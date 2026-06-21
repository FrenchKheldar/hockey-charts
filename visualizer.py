# visualizer.py
# Visualization module to generate Plotly charts and export data JSON/JS

import json
import os
import plotly.graph_objects as go

RED_RGB = "rgb(228,24,46)"

def hex_to_rgb(hex_str):
    """Converts hex color string to list of [R, G, B]."""
    hex_str = hex_str.lstrip('#')
    return [int(hex_str[i:i+2], 16) for i in (0, 2, 4)]

def get_color_spectrum(n, colors, number_bands=15):
    """
    Interpolates between three colors to create a gradient spectrum.
    n: index of the current band
    colors: list of three [R, G, B] colors
    number_bands: total number of steps in the gradient
    """
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

def get_stat(df, p, s, stat):
    """Safely retrieves a player's stat for a given season from the DataFrame."""
    try:
        val = df[(df.Player == p) & (df.Season == s)][stat].values[0]
        return val
    except (IndexError, KeyError):
        return 0

def plot_all_time_leaders(df, stat, stat_name, num, single_season_record, team_name, team_short, seasons, output_dir, team_colors, is_goalie=False):
    """
    Generates a stacked bar chart of all-time leaders in a specific category.
    Saves outputs as PNG (using Kaleido) and interactive HTML files.
    """
    # Filter for career totals and sort by the stat
    top_leaders = df.loc[df.Season == "Total"].sort_values(stat, ascending=False).iloc[:num]
    top_leaders = top_leaders[['Player', 'PlayerAndFlag', stat]].reset_index(drop=True)

    fig = go.Figure()
    names = top_leaders['PlayerAndFlag'].tolist()
    number_seasons = len(seasons)

    # Add bar trace for each season
    for n, s in enumerate(seasons):
        if s == 'Total':
            continue
            
        stats = [get_stat(df, p, s, stat) for p in top_leaders.Player]
        
        # Color single season records in Red, otherwise use the team color gradient
        colors = [RED_RGB if st == single_season_record else get_color_spectrum(n, team_colors, number_seasons) for st in stats]
        
        trace_kwargs = {
            'name': s,
            'x': names,
            'y': stats,
            'marker_color': colors,
            'showlegend': False
        }

        # Special offset handling for Plus/Minus overlay charting
        if stat == "PM":
            trace_kwargs.update({
                'offsetgroup': 0,
                'width': 0.3,
                'offset': 0.3 * (n - 1)
            })
        
        fig.add_trace(go.Bar(**trace_kwargs))

        # Add dummy trace with color for this season to show in legend
        fig.add_trace(go.Bar(x=[None], y=[None],
                             name=s,
                             marker_color=get_color_spectrum(n, team_colors, number_seasons), 
                             showlegend=True))

    if stat == "PM":
        fig.update_layout(barmode='overlay')
    else:
        fig.update_layout(barmode='group')
    
    # Add dummy trace for Single Season Record legend entry
    fig.add_trace(go.Bar(x=[None], y=[None],
                         name='Single Season Record',
                         marker_color=RED_RGB,
                         showlegend=True))

    fig.update_layout(
        barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family="Lora, Georgia, serif",
            color="#1e293b"
        ),
        title=dict(
            text=f"{team_name} All-Time Leaders in {stat_name}",
            font=dict(
                family="EB Garamond, Georgia, serif",
                size=22,
                color="#1e293b"
            )
        ),
        xaxis=dict(
            tickangle=45,
            gridcolor='rgba(0,0,0,0.06)',
            zeroline=True,
            zerolinecolor='rgba(0,0,0,0.12)'
        ),
        yaxis=dict(
            gridcolor='rgba(0,0,0,0.06)',
            zeroline=True,
            zerolinecolor='rgba(0,0,0,0.12)',
            title=dict(
                text=stat_name,
                font=dict(size=12)
            )
        ),
        legend=dict(
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='#e2e8f0',
            borderwidth=1
        )
    )

    # Build output filenames and save
    filename = f"top_{'goalies' if is_goalie else 'leaders'}_{stat}_stacked"
    png_dir = os.path.join(output_dir, team_short, "png")
    html_dir = os.path.join(output_dir, team_short, "html")
    
    os.makedirs(png_dir, exist_ok=True)
    os.makedirs(html_dir, exist_ok=True)

    try:
        fig.write_image(os.path.join(png_dir, f"{filename}.png"), scale=2)
        fig.write_html(os.path.join(html_dir, f"{filename}.html"))
        print(f"📊 Generated chart for {team_short} {stat_name}")
    except Exception as e:
        print(f"⚠️ Failed to save chart for {stat_name}: {e}")

def export_data_to_json(all_data, output_dir):
    """
    Exports the consolidated processed database to both a JSON file (standard data format)
    and a JS file (global variable format to bypass CORS when running index.html locally).
    """
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "data.json")
    js_path = os.path.join(output_dir, "data.js")
    
    # 1. Save JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"✨ Exported unified database JSON to {json_path}")
    
    # 2. Save JS file
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(f"// Auto-generated stats data for local viewing without CORS issues\nconst NHL_DATA = {json.dumps(all_data, ensure_ascii=False)};\n")
    print(f"✨ Exported unified database JS to {js_path}")
