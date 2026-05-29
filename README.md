# status-bar

Fullscreen Pygame display for a Raspberry Pi 7" monitor. Shows clock, weather, and Google Calendar events for today and tomorrow.

## Layout

```
┌──────────────────────┬────────────────────────────┐
│                      │  TODAY                     │
│   Wednesday, 29 May  │    09:00  Stand-up         │
│                      │    14:00  Team meeting     │
│        14:32         │                            │
│                      │  TOMORROW                  │
│   18°C  Partly Cloudy│    10:00  Doctor           │
│   Feels like 15°C    │    All day  Holiday        │
└──────────────────────┴────────────────────────────┘
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Edit `config.json`:
- `location` — city name for weather (e.g. `"Copenhagen"`)
- `display_width` / `display_height` — match your screen (default 800×480)
- `fullscreen` — set `true` on the Pi

### 3. Google Calendar (one-time)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → enable **Google Calendar API**
3. APIs & Services → Credentials → Create **OAuth 2.0 Client ID** (Desktop app)
4. Download the JSON → save as `credentials.json` in this directory
5. Run the auth setup:
   ```bash
   python auth_setup.py
   ```
   A browser window opens. Log in and grant access. `token.json` is saved automatically.

> `credentials.json` and `token.json` are gitignored — never commit them.

### 4. Run

```bash
python main.py
```

Press `Esc` to quit.

## Autostart on Pi (systemd)

Edit `status-bar.service` — update `User` and `WorkingDirectory` to match your Pi's username and repo path. Then:

```bash
sudo cp status-bar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable status-bar
sudo systemctl start status-bar
```

## Tuning

| Setting | Default | Effect |
|---|---|---|
| `left_column_ratio` | `0.45` | Width of clock/weather column |
| `weather_refresh_seconds` | `600` | How often to poll wttr.in |
| `calendar_refresh_seconds` | `300` | How often to fetch calendar |
| `max_events_per_day` | `5` | Max events shown per day |
| `fullscreen` | `false` | Set `true` for Pi kiosk mode |
