from __future__ import annotations

from vacationeer.models.trip import Trip


def _esc(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_chat(trip: Trip) -> str:
    """Return HTML string for the chat tab content."""
    first_attraction = trip.attractions[0].name if trip.attractions else "a popular local sight"

    messages = [
        {
            "role": "ai",
            "text": (
                f"Hi! I'm your travel assistant for {_esc(trip.destination)}. "
                "Ask me to suggest a day plan or add an attraction!"
            ),
        },
        {
            "role": "user",
            "text": "What should we do on our first day?",
        },
        {
            "role": "ai",
            "text": (
                f"For your first day, I'd suggest starting with {_esc(first_attraction)}. "
                "It's a great way to kick off your trip and get a feel for the city! "
                "Want me to build a full day plan around it?"
            ),
        },
    ]

    bubbles_html = ""
    for msg in messages:
        if msg["role"] == "ai":
            bubbles_html += f"""
            <div style="display:flex;justify-content:flex-start;margin-bottom:12px;">
              <div style="max-width:75%;padding:12px 16px;border-radius:16px 16px 16px 4px;
                          background:#f0f0f0;color:#1a2332;font-size:14px;line-height:1.5;">
                {msg['text']}
              </div>
            </div>
            """
        else:
            bubbles_html += f"""
            <div style="display:flex;justify-content:flex-end;margin-bottom:12px;">
              <div style="max-width:75%;padding:12px 16px;border-radius:16px 16px 4px 16px;
                          background:#1a2332;color:#fff;font-size:14px;line-height:1.5;">
                {msg['text']}
              </div>
            </div>
            """

    return f"""
    <div style="background:#f5f6f8;border-radius:12px;font-family:system-ui,-apple-system,sans-serif;
                display:flex;flex-direction:column;height:500px;">
      <!-- Messages area -->
      <div style="flex:1;overflow-y:auto;padding:20px;">
        {bubbles_html}
      </div>
      <!-- Input bar -->
      <div style="padding:12px 16px;border-top:1px solid #e2e5e9;display:flex;gap:8px;
                  background:#fff;border-radius:0 0 12px 12px;">
        <input type="text" placeholder="Type a message..."
               style="flex:1;padding:10px 14px;border:1px solid #d1d5db;border-radius:20px;
                      font-size:14px;outline:none;font-family:inherit;"
               disabled />
        <button style="padding:10px 20px;background:#1a2332;color:#fff;border:none;
                       border-radius:20px;font-size:14px;font-weight:500;cursor:pointer;
                       font-family:inherit;"
                disabled>
          Send
        </button>
      </div>
    </div>
    """
