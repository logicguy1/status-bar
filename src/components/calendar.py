import threading
import time
from datetime import datetime, timedelta
import pygame
from src.components.base import Component
from src.colors import TEXT, DIM, ACCENT, DIVIDER, ACTIVE, WARN
from src.config import ROOT

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _truncate(font: pygame.font.Font, text: str, max_width: int) -> str:
    if font.size(text)[0] <= max_width:
        return text
    while len(text) > 1 and font.size(text + "…")[0] > max_width:
        text = text[:-1]
    return text + "…"


def _event_color(event: dict, now: datetime) -> tuple:
    if event.get("all_day"):
        return ACTIVE
    start = event.get("start_dt")
    end   = event.get("end_dt")
    if start and end and start <= now <= end:
        return ACTIVE
    if start and timedelta(0) < (start - now) <= timedelta(hours=1):
        return WARN
    return TEXT


class CalendarComponent(Component):
    def __init__(self, config: dict) -> None:
        self._interval   = config["calendar_refresh_seconds"]
        self._max_events = config["max_events_per_day"]
        self._lock       = threading.Lock()
        self._today:    list[dict] = []
        self._tomorrow: list[dict] = []
        self._error: str | None    = None

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        while True:
            self._fetch()
            time.sleep(self._interval)

    def _fetch(self) -> None:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_path = ROOT / "token.json"
            if not token_path.exists():
                with self._lock:
                    self._error = "Run auth_setup.py first"
                return

            creds   = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            service = build("calendar", "v3", credentials=creds)

            now         = datetime.now().astimezone()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            result      = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=today_start.isoformat(),
                    timeMax=(today_start + timedelta(days=2)).isoformat(),
                    maxResults=self._max_events * 2,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            today_date    = today_start.date()
            tomorrow_date = (today_start + timedelta(days=1)).date()
            today, tomorrow = [], []

            for event in result.get("items", []):
                start = event["start"]
                end   = event.get("end", {})

                if "dateTime" in start:
                    start_dt   = datetime.fromisoformat(start["dateTime"])
                    end_dt     = datetime.fromisoformat(end["dateTime"]) if "dateTime" in end else None
                    event_date = start_dt.date()
                    time_str   = start_dt.strftime("%H:%M")
                    all_day    = False
                else:
                    start_dt   = None
                    end_dt     = None
                    event_date = datetime.fromisoformat(start["date"]).date()
                    time_str   = "All day"
                    all_day    = True

                entry = {
                    "time":     time_str,
                    "title":    event.get("summary", "(No title)"),
                    "start_dt": start_dt,
                    "end_dt":   end_dt,
                    "all_day":  all_day,
                }
                if event_date == today_date:
                    today.append(entry)
                elif event_date == tomorrow_date:
                    tomorrow.append(entry)

            with self._lock:
                self._today    = today[:self._max_events]
                self._tomorrow = tomorrow[:self._max_events]
                self._error    = None

        except ImportError:
            with self._lock:
                self._error = "google libs not installed"
        except Exception as e:
            with self._lock:
                self._error = str(e)[:60]

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, fonts: dict) -> None:
        pad       = max(16, int(rect.height * 0.05))
        x         = rect.left + pad
        y         = rect.top + int(rect.height * 0.06)
        time_col  = fonts["cal_event"].size("00:00")[0] + int(rect.height * 0.02)
        max_title = rect.width - pad - 8 - time_col - 10
        now       = datetime.now().astimezone()

        with self._lock:
            today    = list(self._today)
            tomorrow = list(self._tomorrow)
            error    = self._error

        if error:
            surface.blit(fonts["cal_event"].render(error, True, DIM), (x, y))
            return

        def draw_section(label: str, events: list, y_pos: int) -> int:
            header = fonts["cal_header"].render(label, True, ACCENT)
            surface.blit(header, (x, y_pos))
            y_pos += header.get_height() + int(rect.height * 0.012)

            if not events:
                s = fonts["cal_event"].render("No events", True, DIM)
                surface.blit(s, (x + 8, y_pos))
                y_pos += s.get_height() + 4
            else:
                row_h = fonts["cal_event"].get_height() + int(rect.height * 0.008)
                for ev in events:
                    color = _event_color(ev, now)
                    surface.blit(fonts["cal_event"].render(ev["time"], True, DIM), (x + 8, y_pos))
                    surface.blit(
                        fonts["cal_event"].render(
                            _truncate(fonts["cal_event"], ev["title"], max_title), True, color
                        ),
                        (x + 8 + time_col, y_pos),
                    )
                    y_pos += row_h

            return y_pos + int(rect.height * 0.02)

        y = draw_section("TODAY",    today,    y)
        div_y = y - int(rect.height * 0.01)
        pygame.draw.line(surface, DIVIDER, (x, div_y), (rect.right - pad, div_y), 1)
        y += int(rect.height * 0.01)
        draw_section("TOMORROW", tomorrow, y)
