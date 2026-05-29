import pygame
from src.colors import BG, DIVIDER
from src.fonts import FontManager
from src.renderer import Renderer
from src.components.clock import ClockComponent
from src.components.weather import WeatherComponent
from src.components.calendar import CalendarComponent


class App:
    def __init__(self, config: dict) -> None:
        self._config      = config
        self._ratio       = config.get("left_column_ratio", 0.45)
        self._split_y     = 0.58
        self._fullscreen  = config.get("fullscreen", False)

    def run(self) -> None:
        pygame.init()

        w = self._config["display_width"]
        h = self._config["display_height"]
        flags  = pygame.FULLSCREEN if self._fullscreen else pygame.RESIZABLE
        screen = pygame.display.set_mode((w, h), flags)
        pygame.display.set_caption("Status Bar")
        pygame.mouse.set_visible(False)

        fonts    = FontManager()
        renderer = self._build_renderer()
        renderer.start_all()

        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            w, h   = screen.get_size()
            col_x  = int(w * self._ratio)
            split_y = int(h * self._split_y)
            pad    = max(16, int(h * 0.05))

            screen.fill(BG)
            pygame.draw.line(screen, DIVIDER, (col_x, 0),   (col_x, h),           1)
            pygame.draw.line(screen, DIVIDER, (pad, split_y), (col_x - pad, split_y), 1)

            renderer.draw(screen, fonts.get(h), w, h)
            pygame.display.flip()
            clock.tick(10)

        pygame.quit()

    def _build_renderer(self) -> Renderer:
        ratio   = self._ratio
        split_y = self._split_y
        config  = self._config

        renderer = Renderer()
        renderer.register(
            ClockComponent(),
            lambda w, h: pygame.Rect(0, 0, int(w * ratio), int(h * split_y)),
        )
        renderer.register(
            WeatherComponent(config),
            lambda w, h: pygame.Rect(0, int(h * split_y), int(w * ratio), h - int(h * split_y)),
        )
        renderer.register(
            CalendarComponent(config),
            lambda w, h: pygame.Rect(int(w * ratio), 0, w - int(w * ratio), h),
        )
        return renderer
