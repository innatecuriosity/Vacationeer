from __future__ import annotations

from vacationeer.models.trip import Trip


def _esc(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _format_price(price: float | None) -> str:
    if price is None:
        return ""
    if price == 0:
        return "Free"
    return f"\u20ac{price:.0f}" if price == int(price) else f"\u20ac{price:.2f}"


def _format_time(t) -> str:
    if t is None:
        return ""
    return t.strftime("%H:%M")


def _format_duration(minutes: int | None) -> str:
    if minutes is None:
        return ""
    if minutes < 60:
        return f"{minutes}min"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}min" if m else f"{h}h"


def _render_placeholder() -> str:
    return """
    <div style="background:#f5f6f8;padding:20px;border-radius:12px;font-family:system-ui,-apple-system,sans-serif;">
      <div style="text-align:center;padding:60px 20px;">
        <pre style="font-size:14px;color:#aaa;line-height:1.4;font-family:monospace;">
     .-------.
    /   o   o \\
   |     ^     |
    \\  \\___/  /
     '-._____.-'
        </pre>
        <h3 style="color:#1a2332;margin:16px 0 8px 0;">No days planned yet</h3>
        <p style="color:#888;font-size:15px;max-width:360px;margin:0 auto;">
          Use the chat to start planning! Ask the AI to suggest a day-by-day itinerary.
        </p>
      </div>
    </div>
    """


def render_timeline(trip: Trip) -> str:
    """Return HTML string for the timeline tab content."""
    has_activities = any(day.activities for day in trip.days)

    if not trip.days or not has_activities:
        return _render_placeholder()

    # --- Day tab bar ---
    tab_buttons = ""
    for i, day in enumerate(trip.days):
        label = day.label or day.date.strftime("%a %b %d")
        active_bg = "#1a2332" if i == 0 else "#e8ecf1"
        active_fg = "#fff" if i == 0 else "#1a2332"
        tab_buttons += (
            f'<button class="tl-day-tab" data-day="{i}" '
            f'style="padding:8px 16px;border-radius:20px;border:none;cursor:pointer;'
            f"font-size:13px;font-weight:500;background:{active_bg};color:{active_fg};"
            f'margin:0 4px 4px 0;transition:all 0.2s;">{_esc(label)}</button>'
        )

    tab_bar = f"""
    <div style="display:flex;flex-wrap:wrap;margin-bottom:20px;padding:12px 16px;
                background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
      {tab_buttons}
    </div>
    """

    # --- Day panels with timeline ---
    panels = ""
    for i, day in enumerate(trip.days):
        display = "block" if i == 0 else "none"
        label = day.label or day.date.strftime("%A, %b %d")

        activities_html = ""
        for j, act in enumerate(day.activities):
            time_str = _format_time(act.start_time)
            dur_str = _format_duration(act.duration_minutes)
            price_str = _format_price(act.price_eur)

            # Connector line (not on last item)
            connector = ""
            if j < len(day.activities) - 1:
                connector = (
                    '<div style="position:absolute;left:14px;top:32px;bottom:-12px;'
                    'width:2px;background:#d1d5db;"></div>'
                )

            meta_parts = []
            if time_str:
                meta_parts.append(time_str)
            if dur_str:
                meta_parts.append(f"\u23f1 {dur_str}")
            if price_str:
                meta_parts.append(price_str)
            meta_html = (
                f'<span style="font-size:12px;color:#888;">{" &middot; ".join(meta_parts)}</span>'
                if meta_parts
                else ""
            )

            status_colors = {
                "done": "#27ae60",
                "confirmed": "#3498db",
                "skipped": "#bbb",
                "planned": "#f39c12",
            }
            dot_color = status_colors.get(act.status, "#f39c12")

            notes_html = ""
            if act.notes:
                notes_html = (
                    f'<p style="margin:4px 0 0 0;font-size:12px;color:#777;'
                    f'font-style:italic;">{_esc(act.notes)}</p>'
                )

            activities_html += f"""
            <div style="position:relative;padding-left:40px;padding-bottom:16px;min-height:40px;">
              {connector}
              <div style="position:absolute;left:7px;top:4px;width:16px;height:16px;
                          border-radius:50%;background:{dot_color};border:3px solid #fff;
                          box-shadow:0 0 0 2px {dot_color};"></div>
              <div style="background:#fff;border-radius:10px;padding:12px 16px;
                          box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px;">
                  <span style="font-size:14px;font-weight:600;color:#1a2332;">{_esc(act.name)}</span>
                  {meta_html}
                </div>
                {notes_html}
              </div>
            </div>
            """

        day_notes = ""
        if day.notes:
            day_notes = (
                f'<div style="margin-top:8px;padding:10px 14px;background:#fff;border-radius:8px;'
                f'font-size:13px;color:#666;border-left:3px solid #1a2332;">{_esc(day.notes)}</div>'
            )

        if not day.activities:
            activities_html = """
            <div style="text-align:center;padding:30px;color:#aaa;font-size:14px;">
              No activities planned for this day yet.
            </div>
            """

        panels += f"""
        <div class="tl-day-panel" data-day="{i}" style="display:{display};">
          <h3 style="margin:0 0 16px 0;font-size:17px;color:#1a2332;">{_esc(label)}</h3>
          {activities_html}
          {day_notes}
        </div>
        """

    # --- Vanilla JS for day switching ---
    script = """
    <script>
    (function() {
      var tabs = document.querySelectorAll('.tl-day-tab');
      var panels = document.querySelectorAll('.tl-day-panel');
      tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
          var dayIdx = this.getAttribute('data-day');
          tabs.forEach(function(t) {
            t.style.background = '#e8ecf1';
            t.style.color = '#1a2332';
          });
          this.style.background = '#1a2332';
          this.style.color = '#fff';
          panels.forEach(function(p) {
            p.style.display = p.getAttribute('data-day') === dayIdx ? 'block' : 'none';
          });
        });
      });
    })();
    </script>
    """

    return f"""
    <div style="background:#f5f6f8;padding:20px;border-radius:12px;font-family:system-ui,-apple-system,sans-serif;">
      {tab_bar}
      {panels}
    </div>
    {script}
    """
