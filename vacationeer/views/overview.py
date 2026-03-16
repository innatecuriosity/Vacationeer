from __future__ import annotations

from collections import Counter

from vacationeer.models.trip import Trip, Category


_CATEGORY_COLORS = {
    Category.LANDMARK: "#e74c3c",
    Category.MUSEUM: "#8e44ad",
    Category.NATURE: "#27ae60",
    Category.FOOD: "#f39c12",
    Category.ENTERTAINMENT: "#e91e63",
    Category.TRANSPORT: "#607d8b",
    Category.ACCOMMODATION: "#3498db",
    Category.SHOPPING: "#00bcd4",
    Category.DAY_TRIP: "#ff7043",
}

_CATEGORY_LABELS = {
    Category.LANDMARK: "Landmarks",
    Category.MUSEUM: "Museums",
    Category.NATURE: "Nature",
    Category.FOOD: "Food",
    Category.ENTERTAINMENT: "Entertainment",
    Category.TRANSPORT: "Transport",
    Category.ACCOMMODATION: "Accommodation",
    Category.SHOPPING: "Shopping",
    Category.DAY_TRIP: "Day Trips",
}


def _esc(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _format_price(price: float | None) -> str:
    if price is None:
        return "Free"
    if price == 0:
        return "Free"
    return f"\u20ac{price:.0f}" if price == int(price) else f"\u20ac{price:.2f}"


def _format_duration(minutes: int | None) -> str:
    if minutes is None:
        return ""
    if minutes < 60:
        return f"{minutes}min"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}min" if m else f"{h}h"


def render_overview(trip: Trip) -> str:
    """Return HTML string for the overview tab content."""
    num_days = (trip.end_date - trip.start_date).days + 1

    # --- Header ---
    header = f"""
    <div style="background:#1a2332;color:#fff;padding:24px 28px;border-radius:12px;margin-bottom:20px;">
      <h2 style="margin:0 0 8px 0;font-size:24px;">{_esc(trip.destination)}</h2>
      <div style="display:flex;gap:24px;flex-wrap:wrap;font-size:14px;opacity:0.9;">
        <span>{trip.start_date.strftime('%b %d')} &ndash; {trip.end_date.strftime('%b %d, %Y')} ({num_days} days)</span>
        <span>{trip.travelers} traveler{'s' if trip.travelers != 1 else ''}</span>
        <span>Budget: {_format_price(trip.budget_eur) if trip.budget_eur else 'Not set'}</span>
      </div>
    </div>
    """

    # --- Category summary bar ---
    counts: Counter[Category] = Counter()
    for a in trip.attractions:
        counts[a.category] += 1

    cat_pills = ""
    for cat in Category:
        cnt = counts.get(cat, 0)
        if cnt == 0:
            continue
        color = _CATEGORY_COLORS.get(cat, "#888")
        label = _CATEGORY_LABELS.get(cat, cat.value)
        cat_pills += (
            f'<span style="display:inline-block;padding:4px 12px;border-radius:20px;'
            f"background:{color};color:#fff;font-size:13px;font-weight:500;"
            f'margin:0 6px 6px 0;">{label} ({cnt})</span>'
        )

    category_bar = ""
    if cat_pills:
        category_bar = f"""
        <div style="margin-bottom:20px;padding:16px;background:#fff;border-radius:10px;
                     box-shadow:0 1px 4px rgba(0,0,0,0.06);">
          <div style="font-size:13px;color:#888;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">
            Categories
          </div>
          {cat_pills}
        </div>
        """

    # --- Attraction cards grouped by category ---
    grouped: dict[Category, list] = {}
    for a in trip.attractions:
        grouped.setdefault(a.category, []).append(a)

    groups_html = ""
    for cat in Category:
        attractions = grouped.get(cat)
        if not attractions:
            continue
        color = _CATEGORY_COLORS.get(cat, "#888")
        label = _CATEGORY_LABELS.get(cat, cat.value)

        cards = ""
        for a in attractions:
            # Price pill
            price_color = "#27ae60" if (a.price_eur is None or a.price_eur == 0) else "#e67e22"
            price_pill = (
                f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
                f"background:{price_color};color:#fff;font-size:12px;font-weight:600;"
                f'margin-right:8px;">{_format_price(a.price_eur)}</span>'
            )

            # Duration
            dur = _format_duration(a.duration_minutes)
            dur_html = (
                f'<span style="font-size:13px;color:#666;">\u23f1 {dur}</span>' if dur else ""
            )

            # Description
            desc = (
                f'<p style="margin:8px 0 10px 0;font-size:13px;color:#555;line-height:1.5;">'
                f"{_esc(a.description)}</p>"
                if a.description
                else ""
            )

            # Tags
            tags_html = ""
            for tag in a.tags:
                tags_html += (
                    f'<span style="display:inline-block;padding:2px 8px;border-radius:10px;'
                    f"background:#e8ecf1;color:#4a5568;font-size:11px;margin:0 4px 4px 0;"
                    f'">{_esc(tag)}</span>'
                )

            cards += f"""
            <div style="background:#fff;border-radius:10px;padding:16px 18px;
                        box-shadow:0 1px 4px rgba(0,0,0,0.07);margin-bottom:12px;">
              <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;">
                <h4 style="margin:0;font-size:15px;color:#1a2332;">{_esc(a.name)}</h4>
                <div>{price_pill}{dur_html}</div>
              </div>
              {desc}
              <div>{tags_html}</div>
            </div>
            """

        groups_html += f"""
        <div style="margin-bottom:24px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};"></span>
            <h3 style="margin:0;font-size:16px;color:#1a2332;">{label}</h3>
          </div>
          {cards}
        </div>
        """

    # Placeholder if no attractions
    if not trip.attractions:
        groups_html = """
        <div style="text-align:center;padding:40px 20px;color:#999;">
          <div style="font-size:32px;margin-bottom:12px;">&#x1f5fa;</div>
          <p style="font-size:15px;">No attractions added yet. Use the chat to discover places!</p>
        </div>
        """

    return f"""
    <div style="background:#f5f6f8;padding:20px;border-radius:12px;font-family:system-ui,-apple-system,sans-serif;">
      {header}
      {category_bar}
      {groups_html}
    </div>
    """
