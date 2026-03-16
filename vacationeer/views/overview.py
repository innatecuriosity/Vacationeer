from __future__ import annotations

from collections import Counter

from vacationeer.models.trip import Trip, Category


_CATEGORY_COLORS = {
    Category.LANDMARK: "#C0392B",
    Category.MUSEUM: "#2980B9",
    Category.NATURE: "#27AE60",
    Category.FOOD: "#E67E22",
    Category.ENTERTAINMENT: "#8E44AD",
    Category.TRANSPORT: "#7F8C8D",
    Category.ACCOMMODATION: "#922B21",
    Category.SHOPPING: "#2E86C1",
    Category.DAY_TRIP: "#1E8449",
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

_CATEGORY_ICONS = {
    Category.LANDMARK: "&#x1f3db;",
    Category.MUSEUM: "&#x1f3db;",
    Category.NATURE: "&#x1f333;",
    Category.FOOD: "&#x1f374;",
    Category.ENTERTAINMENT: "&#x1f3ad;",
    Category.TRANSPORT: "&#x1f68c;",
    Category.ACCOMMODATION: "&#x1f3e8;",
    Category.SHOPPING: "&#x1f6cd;",
    Category.DAY_TRIP: "&#x1f697;",
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


def _score_color(score: float) -> str:
    if score >= 8:
        return "#27AE60"
    if score >= 6:
        return "#F1C40F"
    return "#E74C3C"


def _render_score_bar(score: float, width: int = 60, height: int = 8) -> str:
    """Small colored bar representing a score out of 10."""
    color = _score_color(score)
    pct = min(score / 10.0 * 100, 100)
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;">'
        f'<span style="display:inline-block;width:{width}px;height:{height}px;'
        f'background:#e0e0e0;border-radius:{height // 2}px;overflow:hidden;vertical-align:middle;">'
        f'<span style="display:block;width:{pct:.0f}%;height:100%;background:{color};'
        f'border-radius:{height // 2}px;"></span></span>'
        f'<span style="font-size:12px;font-weight:600;color:{color};">{score:.1f}</span></span>'
    )


def _render_score_detail(score: float, label: str) -> str:
    """Larger score display for expanded card."""
    color = _score_color(score)
    pct = min(score / 10.0 * 100, 100)
    return (
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
        f'<span style="font-size:13px;color:#666;min-width:70px;">{label}</span>'
        f'<span style="display:inline-block;width:100px;height:10px;'
        f'background:#e0e0e0;border-radius:5px;overflow:hidden;">'
        f'<span style="display:block;width:{pct:.0f}%;height:100%;background:{color};'
        f'border-radius:5px;"></span></span>'
        f'<span style="font-size:13px;font-weight:600;color:{color};">{score:.1f}/10</span></div>'
    )


def render_overview(trip: Trip) -> str:
    """Return HTML string for the overview tab content."""
    num_days = (trip.end_date - trip.start_date).days + 1

    # --- Header ---
    header = f"""
    <div style="background:#1a2332;color:#fff;padding:24px 28px;border-radius:12px;margin-bottom:20px;
                font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
      <h2 style="margin:0 0 8px 0;font-size:24px;">{_esc(trip.destination)}</h2>
      <div style="display:flex;gap:24px;flex-wrap:wrap;font-size:14px;opacity:0.9;">
        <span>&#x1f4c5; {trip.start_date.strftime('%b %d')} &ndash; {trip.end_date.strftime('%b %d, %Y')} ({num_days} days)</span>
        <span>&#x1f465; {trip.travelers} traveler{'s' if trip.travelers != 1 else ''}</span>
        <span>&#x1f4b0; Budget: {_format_price(trip.budget_eur) if trip.budget_eur else 'Not set'}</span>
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
    card_index = 0
    for cat_idx, cat in enumerate(Category):
        attractions = grouped.get(cat)
        if not attractions:
            continue
        color = _CATEGORY_COLORS.get(cat, "#888")
        label = _CATEGORY_LABELS.get(cat, cat.value)
        icon = _CATEGORY_ICONS.get(cat, "")
        cnt = len(attractions)
        bg = "#fafbfc" if cat_idx % 2 == 1 else "#ffffff"

        cards = ""
        for a in attractions:
            cid = f"ov-card-{card_index}"
            card_index += 1

            # Price pill
            price_color = "#27AE60" if (a.price_eur is None or a.price_eur == 0) else "#E67E22"
            price_pill = (
                f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
                f"background:{price_color}22;color:{price_color};font-size:12px;font-weight:600;"
                f'border:1px solid {price_color}44;">{_format_price(a.price_eur)}</span>'
            )

            # Duration
            dur = _format_duration(a.duration_minutes)
            dur_html = (
                f'<span style="font-size:12px;color:#666;margin-left:6px;">&#x23f1; {dur}</span>'
                if dur else ""
            )

            # Score bar (compact)
            score_html = ""
            if a.expected_score is not None:
                score_html = f'<span style="margin-left:8px;">{_render_score_bar(a.expected_score)}</span>'

            # User score (compact)
            user_score_compact = ""
            if a.user_score is not None:
                ucolor = _score_color(a.user_score)
                user_score_compact = (
                    f'<span style="margin-left:6px;font-size:11px;color:{ucolor};font-weight:600;">'
                    f'You: &#x2605; {a.user_score:.1f}</span>'
                )

            # One-line description (collapsed)
            short_desc = ""
            if a.description:
                text = _esc(a.description)
                short_desc = (
                    f'<div style="font-size:13px;color:#666;margin-top:6px;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;">'
                    f'{text}</div>'
                )

            # --- Expanded content ---
            expanded_parts = []

            # Full description
            if a.description:
                expanded_parts.append(
                    f'<p style="margin:10px 0;font-size:13px;color:#555;line-height:1.6;">'
                    f'{_esc(a.description)}</p>'
                )

            # Scores detail
            scores_detail = ""
            if a.expected_score is not None:
                scores_detail += _render_score_detail(a.expected_score, "Expected")
            if a.user_score is not None:
                scores_detail += _render_score_detail(a.user_score, "Your score")
            if scores_detail:
                expanded_parts.append(
                    f'<div style="margin:10px 0;padding:10px 12px;background:#f8f9fa;'
                    f'border-radius:8px;">{scores_detail}</div>'
                )

            # Tags
            if a.tags:
                tags_html = ""
                for tag in a.tags:
                    tags_html += (
                        f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;'
                        f"background:#e8ecf1;color:#4a5568;font-size:11px;font-weight:500;"
                        f'margin:0 4px 4px 0;">{_esc(tag)}</span>'
                    )
                expanded_parts.append(
                    f'<div style="margin:8px 0;">'
                    f'<div style="font-size:11px;color:#999;margin-bottom:4px;text-transform:uppercase;'
                    f'letter-spacing:0.5px;">Tags</div>{tags_html}</div>'
                )

            # Tips
            if a.tips:
                expanded_parts.append(
                    f'<div style="margin:10px 0;padding:10px 14px;background:#FFF9E6;'
                    f'border-left:3px solid #F1C40F;border-radius:0 8px 8px 0;'
                    f'font-size:13px;color:#7D6608;line-height:1.5;">'
                    f'<strong>&#x1f4a1; Tip:</strong> {_esc(a.tips)}</div>'
                )

            # URL
            if a.url:
                expanded_parts.append(
                    f'<div style="margin:8px 0;">'
                    f'<a href="{_esc(a.url)}" target="_blank" rel="noopener" '
                    f'style="display:inline-block;padding:6px 14px;background:#1a2332;color:#fff;'
                    f'border-radius:6px;font-size:12px;font-weight:500;text-decoration:none;">'
                    f'&#x1f517; Visit website</a></div>'
                )

            # Image placeholder
            expanded_parts.append(
                '<div style="margin:10px 0;height:200px;background:#eef0f2;border-radius:8px;'
                'display:flex;flex-direction:column;align-items:center;justify-content:center;color:#aaa;">'
                '<span style="font-size:36px;">&#x1f4f7;</span>'
                '<span style="font-size:13px;margin-top:6px;">Image coming soon</span></div>'
            )

            expanded_html = "\n".join(expanded_parts)

            cards += f"""
            <div class="ov-card" style="background:#fff;border-radius:10px;
                        box-shadow:0 1px 4px rgba(0,0,0,0.07);margin-bottom:10px;overflow:hidden;
                        border-left:4px solid {color};">
              <div onclick="ovToggle('{cid}')" style="padding:12px 16px;cursor:pointer;user-select:none;">
                <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px;">
                  <div style="display:flex;align-items:center;gap:6px;min-width:0;flex:1;">
                    <h4 style="margin:0;font-size:14px;color:#1a2332;white-space:nowrap;overflow:hidden;
                               text-overflow:ellipsis;">{_esc(a.name)}</h4>
                    {score_html}
                    {user_score_compact}
                  </div>
                  <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
                    {price_pill}{dur_html}
                    <span id="{cid}-chevron" style="font-size:12px;color:#999;transition:transform 0.2s;
                          display:inline-block;">&#x25BC;</span>
                  </div>
                </div>
                {short_desc}
              </div>
              <div id="{cid}" style="max-height:0;overflow:hidden;transition:max-height 0.35s ease;">
                <div style="padding:0 16px 14px 16px;border-top:1px solid #f0f0f0;">
                  {expanded_html}
                </div>
              </div>
            </div>
            """

        groups_html += f"""
        <div style="margin-bottom:28px;padding:16px 18px;background:{bg};border-radius:10px;
                     border-left:5px solid {color};">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <span style="font-size:18px;">{icon}</span>
            <h3 style="margin:0;font-size:16px;color:{color};font-weight:700;">{label}</h3>
            <span style="font-size:12px;color:#999;font-weight:400;">({cnt})</span>
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

    # --- JavaScript for expand/collapse ---
    script = """
    <script>
    (function(){
      var openCard = null;
      window.ovToggle = function(id) {
        var el = document.getElementById(id);
        var chevron = document.getElementById(id + '-chevron');
        if (!el) return;
        if (openCard && openCard !== id) {
          var prev = document.getElementById(openCard);
          var prevChev = document.getElementById(openCard + '-chevron');
          if (prev) { prev.style.maxHeight = '0'; }
          if (prevChev) { prevChev.style.transform = 'rotate(0deg)'; }
        }
        if (el.style.maxHeight && el.style.maxHeight !== '0px') {
          el.style.maxHeight = '0';
          if (chevron) chevron.style.transform = 'rotate(0deg)';
          openCard = null;
        } else {
          el.style.maxHeight = el.scrollHeight + 'px';
          if (chevron) chevron.style.transform = 'rotate(180deg)';
          openCard = id;
        }
      };
    })();
    </script>
    """

    return f"""
    <div style="background:#f5f6f8;padding:20px;border-radius:12px;
                font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
      {header}
      {category_bar}
      {groups_html}
    </div>
    {script}
    """
