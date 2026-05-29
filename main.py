from src.app import App
from src.config import load_config

if __name__ == "__main__":
    App(load_config()).run()
