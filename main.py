import json
import os
import threading
import time
from datetime import datetime, timedelta

import pygame
import requests

# ── Config ────────────────────────────────────────────────────────────────────

BASE = os.path.dirname(os.path.abspath(__file__))

def load_config():
    with open(os.path.join(BASE, "config.json")) as f:
        return json.load(f)

# ── Shared state ──────────────────────────────────────────────────────────────

state_lock = threading.Lock()
state = {
    "weather": {"temp": None, "feels_like": None, "desc": None, "humidity": None},
    "events_today": [],
    "events_tomorrow": [],
    "calendar_error": None,
    "weather_error": None,
}

# ── Weather ───────────────────────────────────────────────────────────────────

def fetch_weather(location):
    try:
        resp = requests.get(
            f"https://wttr.in/{location}?format=j1",
            timeout=10,
            headers={"User-Agent": "status-bar/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        cond = data["current_condition"][0]
        with state_lock:
            state["weather"] = {
                "temp": cond["temp_C"],
                "feels_like": cond["FeelsLikeC"],
                "desc": cond["weatherDesc"][0]["value"],
                "humidity": cond["humidity"],
            }
            state["weather_error"] = None
    except Exception as e:
        with state_lock:
            state["weather_error"] = str(e)[:60]

def weather_thread_fn(config):
    while True:
        fetch_weather(config["location"])
        time.sleep(config["weather_refresh_seconds"])

# ── Google Calendar ───────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def fetch_calendar(max_events):
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        token_path = os.path.join(BASE, "token.json")
        if not os.path.exists(token_path):
            with state_lock:
                state["calendar_error"] = "Run auth_setup.py first"
            return

        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        service = build("calendar", "v3", credentials=creds)

        now = datetime.now().astimezone()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = today_start + timedelta(days=2)

        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=today_start.isoformat(),
                timeMax=tomorrow_end.isoformat(),
                maxResults=max_events * 2,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        today_date = today_start.date()
        tomorrow_date = (today_start + timedelta(days=1)).date()
        today_events, tomorrow_events = [], []

        for event in result.get("items", []):
            start = event["start"]
            if "dateTime" in start:
                dt = datetime.fromisoformat(start["dateTime"])
                event_date = dt.date()
                time_str = dt.strftime("%H:%M")
            else:
                event_date = datetime.fromisoformat(start["date"]).date()
                time_str = "All day"

            entry = {"time": time_str, "title": event.get("summary", "(No title)")}
            if event_date == today_date:
                today_events.append(entry)
            elif event_date == tomorrow_date:
                tomorrow_events.append(entry)

        with state_lock:
            state["events_today"] = today_events[:max_events]
            state["events_tomorrow"] = tomorrow_events[:max_events]
            state["calendar_error"] = None

    except ImportError:
        with state_lock:
            state["calendar_error"] = "google libs not installed"
    except Exception as e:
        with state_lock:
            state["calendar_error"] = str(e)[:60]

def calendar_thread_fn(config):
    while True:
        fetch_calendar(config["max_events_per_day"])
        time.sleep(config["calendar_refresh_seconds"])

# ── Colors ────────────────────────────────────────────────────────────────────

BG      = (26,  26,  46)
TEXT    = (224, 224, 224)
DIM     = (158, 158, 158)
ACCENT  = (79,  195, 247)
DIVIDER = (50,  50,  80)

# ── Fonts (scale with window height) ─────────────────────────────────────────

# Ratios relative to window height (tuned at 480px reference)
FONT_RATIOS = {
    "clock":        0.200,
    "date":         0.075,
    "weather_temp": 0.067,
    "weather_desc": 0.046,
    "cal_header":   0.050,
    "cal_event":    0.042,
    "small":        0.033,
}

_font_path = None

def _find_font_path():
    global _font_path
    if _font_path is not None:
        return _font_path
    for name in ("DejaVu Sans", "Liberation Sans", "FreeSans", "Arial", "Helvetica"):
        path = pygame.font.match_font(name)
        if path:
            _font_path = path
            return path
    _font_path = ""
    return None

def make_fonts(h):
    path = _find_font_path()
    def f(ratio):
        return pygame.font.Font(path, max(8, int(h * ratio)))
    return {k: f(v) for k, v in FONT_RATIOS.items()}

# ── Render helpers ────────────────────────────────────────────────────────────

def blit_center(surface, surf, cx, y):
    surface.blit(surf, surf.get_rect(centerx=cx, top=y))
    return y + surf.get_height()

def blit_left(surface, surf, x, y):
    surface.blit(surf, (x, y))
    return y + surf.get_height()

def render(fonts, key, text, color):
    return fonts[key].render(text, True, color)

def truncate(fonts, key, text, max_width):
    if fonts[key].size(text)[0] <= max_width:
        return text
    while len(text) > 1 and fonts[key].size(text + "…")[0] > max_width:
        text = text[:-1]
    return text + "…"

# ── Left column: clock + weather ──────────────────────────────────────────────

def draw_left(surface, fonts, col_w, h):
    pad = max(16, int(h * 0.05))
    cx  = col_w // 2
    now = datetime.now()

    upper_h = int(h * 0.58)

    date_surf  = render(fonts, "date",  now.strftime("%A, %-d %B"), DIM)
    clock_surf = render(fonts, "clock", now.strftime("%H:%M"),      TEXT)
    block_h = date_surf.get_height() + int(h * 0.03) + clock_surf.get_height()
    y = max(0, (upper_h - block_h) // 2)

    blit_center(surface, date_surf,  cx, y)
    y += date_surf.get_height() + int(h * 0.03)
    blit_center(surface, clock_surf, cx, y)

    pygame.draw.line(surface, DIVIDER, (pad, upper_h), (col_w - pad, upper_h), 1)

    with state_lock:
        weather = dict(state["weather"])
        err     = state["weather_error"]

    y = upper_h + int(h * 0.04)
    if err:
        blit_center(surface, render(fonts, "small", "Weather unavailable", DIM), cx, y)
    elif weather["temp"] is None:
        blit_center(surface, render(fonts, "weather_desc", "Loading weather…", DIM), cx, y)
    else:
        y = blit_center(surface, render(fonts, "weather_temp", f"{weather['temp']}°C", ACCENT), cx, y) + 4
        y = blit_center(surface, render(fonts, "weather_desc", weather["desc"], DIM), cx, y) + 4
        if weather["feels_like"] and weather["humidity"]:
            blit_center(surface, render(fonts, "small",
                f"Feels like {weather['feels_like']}°C  ·  {weather['humidity']}% humidity", DIM),
                cx, y)

# ── Right column: calendar ────────────────────────────────────────────────────

def draw_right(surface, fonts, x0, col_w, h):
    pad       = max(16, int(h * 0.05))
    x         = x0 + pad
    y         = int(h * 0.06)
    time_col  = fonts["cal_event"].size("00:00")[0] + int(h * 0.02)
    max_title = col_w - pad - 8 - time_col - 10

    with state_lock:
        events_today    = list(state["events_today"])
        events_tomorrow = list(state["events_tomorrow"])
        cal_error       = state["calendar_error"]

    if cal_error:
        blit_left(surface, render(fonts, "cal_event", cal_error, DIM), x, y)
        return

    def draw_section(label, events, y_pos):
        y_pos = blit_left(surface, render(fonts, "cal_header", label, ACCENT), x, y_pos) + int(h * 0.012)
        if not events:
            y_pos = blit_left(surface, render(fonts, "cal_event", "No events", DIM), x + 8, y_pos) + 4
        else:
            for ev in events:
                row_h = fonts["cal_event"].get_height() + int(h * 0.008)
                surface.blit(render(fonts, "cal_event", ev["time"], DIM), (x + 8, y_pos))
                surface.blit(
                    render(fonts, "cal_event", truncate(fonts, "cal_event", ev["title"], max_title), TEXT),
                    (x + 8 + time_col, y_pos),
                )
                y_pos += row_h
        return y_pos + int(h * 0.02)

    y = draw_section("TODAY",    events_today,    y)
    pygame.draw.line(surface, DIVIDER, (x, y - int(h * 0.01)), (x0 + col_w - pad, y - int(h * 0.01)), 1)
    y += int(h * 0.01)
    draw_section("TOMORROW", events_tomorrow, y)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    config         = load_config()
    left_col_ratio = config.get("left_column_ratio", 0.45)
    fullscreen     = config.get("fullscreen", False)

    pygame.init()
    _find_font_path()

    init_w = config["display_width"]
    init_h = config["display_height"]
    flags  = pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE
    screen = pygame.display.set_mode((init_w, init_h), flags)
    pygame.display.set_caption("Status Bar")
    pygame.mouse.set_visible(False)

    fonts    = make_fonts(init_h)
    last_h   = init_h
    tick     = pygame.time.Clock()

    threading.Thread(target=weather_thread_fn,  args=(config,), daemon=True).start()
    threading.Thread(target=calendar_thread_fn, args=(config,), daemon=True).start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        w, h = screen.get_size()

        # Rebuild fonts only when height actually changes
        if h != last_h:
            fonts  = make_fonts(h)
            last_h = h

        col_w = int(w * left_col_ratio)

        screen.fill(BG)
        pygame.draw.line(screen, DIVIDER, (col_w, 0), (col_w, h), 1)
        draw_left(screen,  fonts, col_w,         h)
        draw_right(screen, fonts, col_w, w - col_w, h)
        pygame.display.flip()
        tick.tick(10)

    pygame.quit()

if __name__ == "__main__":
    main()
