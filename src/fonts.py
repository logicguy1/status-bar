import pygame

RATIOS = {
    "clock":        0.200,
    "date":         0.075,
    "weather_temp": 0.067,
    "weather_desc": 0.046,
    "cal_header":   0.050,
    "cal_event":    0.042,
    "small":        0.033,
}

class FontManager:
    def __init__(self):
        self._path = self._find_path()
        self._h: int | None = None
        self._fonts: dict | None = None

    def _find_path(self) -> str | None:
        for name in ("DejaVu Sans", "Liberation Sans", "FreeSans", "Arial", "Helvetica"):
            path = pygame.font.match_font(name)
            if path:
                return path
        return None

    def get(self, h: int) -> dict:
        if h != self._h:
            self._h = h
            self._fonts = {
                k: pygame.font.Font(self._path, max(8, int(h * r)))
                for k, r in RATIOS.items()
            }
        return self._fonts
