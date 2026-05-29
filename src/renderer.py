from __future__ import annotations
from typing import Callable
import pygame
from src.components.base import Component


class Renderer:
    def __init__(self) -> None:
        self._entries: list[tuple[Component, Callable]] = []

    def register(self, component: Component, rect_fn: Callable[[int, int], pygame.Rect]) -> None:
        self._entries.append((component, rect_fn))

    def start_all(self) -> None:
        for component, _ in self._entries:
            component.start()

    def draw(self, surface: pygame.Surface, fonts: dict, w: int, h: int) -> None:
        for component, rect_fn in self._entries:
            component.draw(surface, rect_fn(w, h), fonts)
