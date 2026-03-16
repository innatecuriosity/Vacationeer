from __future__ import annotations

from pathlib import Path

from vacationeer.models.trip import Trip


def generate_app(
    trip: Trip,
    map_filename: str,
    output_path: Path,
    tab_contents: dict[str, str] | None = None,
) -> Path:
    """Generate the main app HTML file.

    Args:
        trip: Trip model instance
        map_filename: filename of the map HTML (same directory)
        output_path: Path to write the HTML to
        tab_contents: Optional dict mapping tab id to HTML content
                     e.g. {"overview-content": "<div>...</div>"}

    Returns:
        The path the HTML was written to.
    """
    tab_contents = tab_contents or {}
    output_path = Path(output_path)

    date_fmt = "%b %d, %Y"
    start = trip.start_date.strftime(date_fmt)
    end = trip.end_date.strftime(date_fmt)
    num_days = (trip.end_date - trip.start_date).days + 1

    overview_inner = tab_contents.get("overview-content", "")
    timeline_inner = tab_contents.get("timeline-content", "")
    chat_inner = tab_contents.get("chat-content", "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(trip.name)} - Vacationeer</title>
<style>
*, *::before, *::after {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}
html, body {{
    height: 100%;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1a2332;
    background: #fff;
}}

/* ---- layout ---- */
.app {{
    display: flex;
    height: 100vh;
    overflow: hidden;
}}

/* ---- sidebar ---- */
.sidebar {{
    width: 250px;
    min-width: 250px;
    background: #1a2332;
    color: #fff;
    display: flex;
    flex-direction: column;
    transition: width 0.25s ease, min-width 0.25s ease;
    overflow: hidden;
}}
.sidebar-header {{
    padding: 20px 18px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}}
.sidebar-header .brand {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    opacity: 0.5;
    margin-bottom: 6px;
    white-space: nowrap;
}}
.sidebar-header .trip-name {{
    font-size: 16px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.nav {{
    list-style: none;
    padding: 12px 0;
    flex: 1;
}}
.nav li {{
    position: relative;
}}
.nav-btn {{
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 20px;
    background: none;
    border: none;
    color: rgba(255,255,255,0.7);
    font-size: 14px;
    font-family: inherit;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s, color 0.15s;
    white-space: nowrap;
}}
.nav-btn:hover {{
    background: rgba(255,255,255,0.1);
    color: #fff;
}}
.nav-btn.active {{
    color: #fff;
    background: rgba(255,255,255,0.1);
    border-left: 3px solid #4ea4f6;
    padding-left: 17px;
}}
.nav-btn .icon {{
    font-size: 18px;
    width: 24px;
    text-align: center;
    flex-shrink: 0;
}}
.nav-btn .label {{
    overflow: hidden;
    text-overflow: ellipsis;
}}

.sidebar-footer {{
    padding: 14px 18px;
    border-top: 1px solid rgba(255,255,255,0.08);
    font-size: 12px;
    opacity: 0.35;
    white-space: nowrap;
}}

/* ---- main ---- */
.main {{
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: #fff;
}}

.header {{
    padding: 18px 28px;
    border-bottom: 1px solid #e8eaed;
    background: #fff;
}}
.header h1 {{
    font-size: 20px;
    font-weight: 700;
    color: #1a2332;
    margin-bottom: 4px;
}}
.header .meta {{
    font-size: 13px;
    color: #5f6b7a;
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
}}
.header .meta span {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
}}

.content {{
    flex: 1;
    overflow: auto;
    background: #f5f6f8;
}}

.tab-panel {{
    display: none;
    height: 100%;
}}
.tab-panel.active {{
    display: block;
}}

#tab-map {{
    padding: 0;
}}
#tab-map iframe {{
    width: 100%;
    height: 100%;
    border: none;
}}

#tab-overview, #tab-timeline, #tab-chat {{
    padding: 24px 28px;
}}
.tab-placeholder {{
    color: #8893a2;
    font-size: 14px;
    padding: 40px 0;
    text-align: center;
}}

/* ---- responsive ---- */
@media (max-width: 768px) {{
    .sidebar {{
        width: 60px;
        min-width: 60px;
    }}
    .sidebar-header .brand,
    .sidebar-header .trip-name,
    .nav-btn .label,
    .sidebar-footer {{
        display: none;
    }}
    .sidebar-header {{
        padding: 16px 0;
        text-align: center;
    }}
    .nav-btn {{
        justify-content: center;
        padding: 14px 0;
    }}
    .nav-btn.active {{
        border-left: 3px solid #4ea4f6;
        padding-left: 0;
    }}
    .header {{
        padding: 14px 16px;
    }}
    .header h1 {{
        font-size: 17px;
    }}
    #tab-overview, #tab-timeline, #tab-chat {{
        padding: 16px;
    }}
}}
</style>
</head>
<body>
<div class="app">

    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="brand">Vacationeer</div>
            <div class="trip-name">{_esc(trip.destination)}</div>
        </div>
        <ul class="nav">
            <li><button class="nav-btn active" data-tab="tab-map"><span class="icon">\U0001f5fa</span><span class="label">Map</span></button></li>
            <li><button class="nav-btn" data-tab="tab-overview"><span class="icon">\U0001f4cb</span><span class="label">Overview</span></button></li>
            <li><button class="nav-btn" data-tab="tab-timeline"><span class="icon">\U0001f4c5</span><span class="label">Timeline</span></button></li>
            <li><button class="nav-btn" data-tab="tab-chat"><span class="icon">\U0001f4ac</span><span class="label">Chat</span></button></li>
        </ul>
        <div class="sidebar-footer">Vacationeer v0.1</div>
    </aside>

    <div class="main">
        <header class="header">
            <h1>{_esc(trip.name)}</h1>
            <div class="meta">
                <span>\U0001f4cd {_esc(trip.destination)}</span>
                <span>\U0001f4c6 {start} &ndash; {end} ({num_days} days)</span>
                <span>\U0001f465 {trip.travelers} travelers</span>
                {_budget_span(trip)}
            </div>
        </header>
        <div class="content">
            <div id="tab-map" class="tab-panel active">
                <iframe src="{_esc(map_filename)}"></iframe>
            </div>
            <div id="tab-overview" class="tab-panel">
                <div id="overview-content">{overview_inner if overview_inner else '<div class="tab-placeholder">Overview will appear here.</div>'}</div>
            </div>
            <div id="tab-timeline" class="tab-panel">
                <div id="timeline-content">{timeline_inner if timeline_inner else '<div class="tab-placeholder">Timeline will appear here.</div>'}</div>
            </div>
            <div id="tab-chat" class="tab-panel">
                <div id="chat-content">{chat_inner if chat_inner else '<div class="tab-placeholder">Chat will appear here.</div>'}</div>
            </div>
        </div>
    </div>

</div>

<script>
(function() {{
    var buttons = document.querySelectorAll('.nav-btn');
    var panels = document.querySelectorAll('.tab-panel');

    buttons.forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            var target = btn.getAttribute('data-tab');
            buttons.forEach(function(b) {{ b.classList.remove('active'); }});
            panels.forEach(function(p) {{ p.classList.remove('active'); }});
            btn.classList.add('active');
            document.getElementById(target).classList.add('active');
        }});
    }});
}})();
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _budget_span(trip: Trip) -> str:
    if trip.budget_eur is not None:
        return f'<span>\U0001f4b6 \u20ac{trip.budget_eur:,.0f} budget</span>'
    return ""
