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

BG        = (26,  26,  46)
TEXT      = (224, 224, 224)
DIM       = (158, 158, 158)
ACCENT    = (79,  195, 247)
DIVIDER   = (50,  50,  80)

# ── Font loading ──────────────────────────────────────────────────────────────

def load_fonts():
    for name in ("DejaVu Sans", "Liberation Sans", "FreeSans", "Arial", "Helvetica"):
        path = pygame.font.match_font(name)
        if path:
            break
    else:
        path = None

    def f(size):
        return pygame.font.Font(path, size)

    return {
        "clock":        f(96),
        "date":         f(36),
        "weather_temp": f(32),
        "weather_desc": f(22),
        "cal_header":   f(24),
        "cal_event":    f(20),
        "small":        f(16),
    }

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

def draw_left(surface, fonts, col_w, height):
    pad = 30
    cx = col_w // 2
    now = datetime.now()

    upper_h = int(height * 0.58)

    # Date and clock stacked, centered in upper zone
    date_surf  = render(fonts, "date",  now.strftime("%A, %-d %B"), DIM)
    clock_surf = render(fonts, "clock", now.strftime("%H:%M"),      TEXT)
    block_h = date_surf.get_height() + 14 + clock_surf.get_height()
    y = (upper_h - block_h) // 2

    blit_center(surface, date_surf,  cx, y)
    y += date_surf.get_height() + 14
    blit_center(surface, clock_surf, cx, y)

    # Divider
    pygame.draw.line(surface, DIVIDER, (pad, upper_h), (col_w - pad, upper_h), 1)

    # Weather in lower zone
    with state_lock:
        weather = dict(state["weather"])
        err     = state["weather_error"]

    y = upper_h + 20
    if err:
        s = render(fonts, "small", f"Weather unavailable", DIM)
        blit_center(surface, s, cx, y)
    elif weather["temp"] is None:
        s = render(fonts, "weather_desc", "Loading weather…", DIM)
        blit_center(surface, s, cx, y)
    else:
        s = render(fonts, "weather_temp", f"{weather['temp']}°C", ACCENT)
        y = blit_center(surface, s, cx, y) + 4
        s = render(fonts, "weather_desc", weather["desc"], DIM)
        y = blit_center(surface, s, cx, y) + 4
        if weather["feels_like"] and weather["humidity"]:
            s = render(fonts, "small",
                       f"Feels like {weather['feels_like']}°C  ·  {weather['humidity']}% humidity",
                       DIM)
            blit_center(surface, s, cx, y)

# ── Right column: calendar ────────────────────────────────────────────────────

def draw_right(surface, fonts, x0, col_w, height):
    pad = 28
    x  = x0 + pad
    y  = 28
    max_title_w = col_w - pad - 8 - 58 - 10

    with state_lock:
        events_today    = list(state["events_today"])
        events_tomorrow = list(state["events_tomorrow"])
        cal_error       = state["calendar_error"]

    if cal_error:
        s = render(fonts, "cal_event", cal_error, DIM)
        blit_left(surface, s, x, y)
        return

    def draw_section(label, events, y_pos):
        s = render(fonts, "cal_header", label, ACCENT)
        y_pos = blit_left(surface, s, x, y_pos) + 6

        if not events:
            s = render(fonts, "cal_event", "No events", DIM)
            y_pos = blit_left(surface, s, x + 8, y_pos) + 4
        else:
            for ev in events:
                time_s  = render(fonts, "cal_event", ev["time"],                      DIM)
                title_s = render(fonts, "cal_event", truncate(fonts, "cal_event",
                                                              ev["title"], max_title_w), TEXT)
                surface.blit(time_s,  (x + 8,      y_pos))
                surface.blit(title_s, (x + 8 + 58, y_pos))
                y_pos += fonts["cal_event"].get_height() + 4
        return y_pos + 10

    y = draw_section("TODAY",    events_today,    y)
    pygame.draw.line(surface, DIVIDER, (x, y - 6), (x0 + col_w - pad, y - 6), 1)
    y += 4
    draw_section("TOMORROW", events_tomorrow, y)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    config   = load_config()
    width    = config["display_width"]
    height   = config["display_height"]
    fs_flag  = pygame.FULLSCREEN if config.get("fullscreen", False) else 0

    pygame.init()
    screen = pygame.display.set_mode((width, height), fs_flag)
    pygame.display.set_caption("Status Bar")
    pygame.mouse.set_visible(False)

    fonts = load_fonts()
    clock = pygame.time.Clock()
    col_w = int(width * config.get("left_column_ratio", 0.45))

    threading.Thread(target=weather_thread_fn,  args=(config,), daemon=True).start()
    threading.Thread(target=calendar_thread_fn, args=(config,), daemon=True).start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill(BG)
        pygame.draw.line(screen, DIVIDER, (col_w, 0), (col_w, height), 1)
        draw_left(screen,  fonts, col_w,         height)
        draw_right(screen, fonts, col_w, width - col_w, height)
        pygame.display.flip()
        clock.tick(10)

    pygame.quit()

if __name__ == "__main__":
    main()
