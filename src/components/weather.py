import threading
import time
import requests
import pygame
from src.components.base import Component
from src.colors import ACCENT, DIM


class WeatherComponent(Component):
    def __init__(self, config: dict) -> None:
        self._location = config["location"]
        self._interval = config["weather_refresh_seconds"]
        self._lock  = threading.Lock()
        self._state = {"temp": None, "feels_like": None, "desc": None, "humidity": None}
        self._error: str | None = None

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        while True:
            self._fetch()
            time.sleep(self._interval)

    def _fetch(self) -> None:
        try:
            resp = requests.get(
                f"https://wttr.in/{self._location}?format=j1",
                timeout=10,
                headers={"User-Agent": "status-bar/1.0"},
            )
            resp.raise_for_status()
            cond = resp.json()["current_condition"][0]
            with self._lock:
                self._state = {
                    "temp":       cond["temp_C"],
                    "feels_like": cond["FeelsLikeC"],
                    "desc":       cond["weatherDesc"][0]["value"],
                    "humidity":   cond["humidity"],
                }
                self._error = None
        except Exception as e:
            with self._lock:
                self._error = str(e)[:60]

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, fonts: dict) -> None:
        cx = rect.centerx
        y  = rect.top + max(12, int(rect.height * 0.15))

        with self._lock:
            state = dict(self._state)
            err   = self._error

        def blit(surf: pygame.Surface) -> int:
            surface.blit(surf, surf.get_rect(centerx=cx, top=y))
            return y + surf.get_height() + 4

        if err:
            blit(fonts["small"].render("Weather unavailable", True, DIM))
        elif state["temp"] is None:
            blit(fonts["weather_desc"].render("Loading weather…", True, DIM))
        else:
            y = blit(fonts["weather_temp"].render(f"{state['temp']}°C", True, ACCENT))
            y = blit(fonts["weather_desc"].render(state["desc"], True, DIM))
            if state["feels_like"] and state["humidity"]:
                blit(fonts["small"].render(
                    f"Feels like {state['feels_like']}°C  ·  {state['humidity']}% humidity",
                    True, DIM,
                ))
