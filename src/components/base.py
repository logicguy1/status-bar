from abc import ABC, abstractmethod
import pygame


class Component(ABC):
    def start(self) -> None:
        """Start background threads if any. Called once before the main loop."""
        pass

    @abstractmethod
    def draw(self, surface: pygame.Surface, rect: pygame.Rect, fonts: dict) -> None:
        """Draw this component within rect."""
        ...
