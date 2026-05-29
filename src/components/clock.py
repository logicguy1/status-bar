from datetime import datetime
import pygame
from src.components.base import Component
from src.colors import TEXT, DIM


class ClockComponent(Component):
    def draw(self, surface: pygame.Surface, rect: pygame.Rect, fonts: dict) -> None:
        now = datetime.now()
        cx  = rect.centerx

        date_surf  = fonts["date"].render(now.strftime("%A, %-d %B"), True, DIM)
        clock_surf = fonts["clock"].render(now.strftime("%H:%M"), True, TEXT)

        gap     = max(8, int(rect.height * 0.06))
        block_h = date_surf.get_height() + gap + clock_surf.get_height()
        y       = rect.top + max(0, (rect.height - block_h) // 2)

        surface.blit(date_surf,  date_surf.get_rect(centerx=cx, top=y))
        y += date_surf.get_height() + gap
        surface.blit(clock_surf, clock_surf.get_rect(centerx=cx, top=y))
