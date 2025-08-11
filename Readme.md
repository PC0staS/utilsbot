<div align="center">

# UtilsBot (Discord)

Handy utilities for your Discord server: merge PDFs and videos, capture web screenshots, ping sites, shorten URLs, translate, check weather, and more. Output files are saved into your Nextcloud.

<br/>

![License](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![discord.py](https://img.shields.io/badge/discord.py-2.x-5865F2)

</div>

## Table of contents
- Features
- Command reference
- Quick start
- Configuration
- Nextcloud integration
- Systemd service (optional)
- Troubleshooting
- Contributing • Code of Conduct • Security • License

## Features
- Merge PDFs: combine 2–5 PDFs into one.
- Merge videos: concatenate 2–5 clips into an MP4 (ffmpeg).
- Web screenshot: capture a PNG of a given URL.
- URL shortener: quick is.gd links.
- Network and HTTP pings with latency.
- Dictionary, Translate, Weather, Timezone, Reminders, System stats, and more.

## Command reference
- /help – list commands
- /mergepdf file1 [file2..file5]
- /mergevid file1 [file2..file5]
- /screenshotweb url
- /shorten url
- /ping ip_address
- /webping url [veces]
- /qr url
- /passw chars
- /remind time message
- /translate text target_language
- /definition word [language]
- /weather lugar
- /timezone zona
- /stats, /netdevices, /vpnstatus
- /restart, /shutdown, /reboot, /update, /execute command

## Quick start
1) Create and activate a virtual environment
- Windows PowerShell
	- python -m venv .venv
	- .venv\\Scripts\\Activate.ps1
- Linux/macOS
	- python3 -m venv .venv
	- source .venv/bin/activate

2) Install dependencies
- pip install -r requirements.txt

3) Configure environment
Copy .env.example to .env and set:
	- DISCORD_TOKEN=your_discord_bot_token (required)
	- NEXTCLOUD_DIR=your nextcloud dir (optional override)
	- SERVICE_NAME=utilsbot.service (optional; used by /restart)

4) Run the bot
- python bot.py

## Configuration
- DISCORD_TOKEN: Your Discord bot token (required).
- NEXTCLOUD_DIR: Base folder where outputs are saved (optional). Default tries sensible paths and falls back to CWD.
- SERVICE_NAME: Systemd service name for /restart (optional; default utilsbot.service).

Requirements
- Python 3.10+
- ffmpeg/ffprobe on PATH for /mergevid

## Nextcloud integration
- Base folder (configurable via NEXTCLOUD_DIR):
	- your nextcloud dir
- Subfolders are created automatically:
	- Merged pdfs – combined PDFs
	- Merged videos – concatenated videos
	- Screenshots – URL captures
- Unique filenames prevent overwrites.

## Systemd service (optional)
Create /etc/systemd/system/utilsbot.service:

	[Unit]
	Description=UtilsBot Discord Bot
	After=network.target

	[Service]
	Type=simple
	WorkingDirectory=/opt/utilsbot
	ExecStart=/opt/utilsbot/.venv/bin/python /opt/utilsbot/bot.py
	Environment=DISCORD_TOKEN=YOUR_TOKEN_HERE
	# Or: EnvironmentFile=/opt/utilsbot/.env
	Restart=on-failure

	[Install]
	WantedBy=multi-user.target

Then reload and start:
- sudo systemctl daemon-reload
- sudo systemctl enable --now utilsbot.service

## Troubleshooting
- Bot token error: ensure DISCORD_TOKEN is set in .env and the process can read it.
- dotenv issues: the bot looks for .env in both the working directory and alongside bot.py (supports .env/.ENV). It will still run without dotenv if the environment variable is set by the shell/service.
- ffmpeg not found: install ffmpeg and ensure it’s on PATH; required for /mergevid.

## Contributing
See CONTRIBUTING.md. Please open an issue first for major changes.

## Code of Conduct
See CODE_OF_CONDUCT.md

## Security
See SECURITY.md for how to report vulnerabilities.

## License
MIT — see LICENSE



