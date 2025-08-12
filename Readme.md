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
- Docker deployment
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
 - Scheduled reminders and recurrent "habits".
 - Password generator.
 - Cryptographic helpers: Fernet encryption/decryption (user supplied key) + hashing (sha256/sha512/blake2/md5).
 - Speedtest (speedtest-cli) and WHOIS lookup.

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
- /habit time message
- /listhabit
- /deletehabit message
- /translate text target_language
- /definition word [language]
- /weather lugar
- /timezone zona
- /stats, /netdevices, /vpnstatus
- /restart, /shutdown, /reboot, /update, /execute command
- /whois domain
- /speedtest
- /encrypt message key
- /decrypt message key
- /hash message [algorithm]
- /roll dices [sides]

## Quick start

### Option 1: Docker (Recommended)

1) Clone the repository
```bash
git clone https://github.com/PC0staS/utilsbot.git
cd utilsbot
```

2) Configure environment
```bash
cp .env.example .env
# Edit .env and set your DISCORD_TOKEN
```

3) Build and run with Docker Compose
```bash
docker compose up -d
```

4) Check logs
```bash
docker compose logs -f utilsbot
```

### Option 2: Direct Python Installation

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
	- (optional) Set a default FERNET_KEY if you want to avoid passing the key each time (not implemented by default; current /encrypt & /decrypt expect user supplied key argument)

4) Run the bot
- python bot.py

## Configuration
- DISCORD_TOKEN: Your Discord bot token (required).
- NEXTCLOUD_DIR: Base folder where outputs are saved (optional). Default tries sensible paths and falls back to CWD.
- SERVICE_NAME: Systemd service name for /restart (optional; default utilsbot.service).

Requirements
- **For Docker:** Docker and Docker Compose
- **For direct installation:** Python 3.10+, ffmpeg/ffprobe on PATH for /mergevid, speedtest-cli for /speedtest (installed via requirements.txt)

## Nextcloud integration
- Base folder (configurable via NEXTCLOUD_DIR):
	- your nextcloud dir
- Subfolders are created automatically:
	- Merged pdfs – combined PDFs
	- Merged videos – concatenated videos
	- Screenshots – URL captures
- Unique filenames prevent overwrites.

## Docker Deployment

### Using Docker Compose (Recommended)

1) **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set DISCORD_TOKEN=your_discord_bot_token
   ```

2) **Start the bot:**
   ```bash
   docker compose up -d
   ```

3) **View logs:**
   ```bash
   docker compose logs -f utilsbot
   ```

4) **Stop the bot:**
   ```bash
   docker compose down
   ```

### Manual Docker Commands

1) **Build the image:**
   ```bash
   docker build -t utilsbot .
   ```

2) **Run the container:**
   ```bash
   docker run -d --name utilsbot \
     --env-file .env \
     -v ./output:/app/output \
     --restart unless-stopped \
     utilsbot
   ```

### Docker Configuration

- **Volumes:**
  - `./output:/app/output` - Output files (screenshots, PDFs, videos)
  - `./.env:/app/.env:ro` - Environment configuration (read-only)
  - Optional: Mount your Nextcloud directory for direct file access

- **Environment Variables:**
  - `DISCORD_TOKEN` - Your Discord bot token (required)
  - `NEXTCLOUD_DIR` - Base folder for outputs (default: /app/output)
  - `SERVICE_NAME` - Service name for restart command (default: utilsbot)

- **Health Check:** The container includes a health check that monitors the bot process

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

### General Issues
- Bot token error: ensure DISCORD_TOKEN is set in .env and the process can read it.
- dotenv issues: the bot looks for .env in both the working directory and alongside bot.py (supports .env/.ENV). It will still run without dotenv if the environment variable is set by the shell/service.
- ffmpeg not found: install ffmpeg and ensure it’s on PATH; required for /mergevid.
- Permission errors on /execute or system commands: ensure the bot process user has the needed sudo rights (or adjust commands).
- Encryption errors: ensure the Fernet key is a 32-byte URL-safe base64 value (generate with: from cryptography.fernet import Fernet; Fernet.generate_key()).

### Docker-specific Issues
- **Container fails to start:** Check logs with `docker compose logs utilsbot`
- **Permission issues with output directory:** Ensure the ./output directory exists and is writable
- **Network issues:** The container uses bridge networking for better Discord connectivity
- **Memory issues:** Adjust resource limits in docker-compose.yml if needed
- **Volume mount issues:** Ensure paths in docker-compose.yml are correct for your system

## Contributing
See CONTRIBUTING.md. Please open an issue first for major changes.

## Code of Conduct
See CODE_OF_CONDUCT.md

## Security
See SECURITY.md for how to report vulnerabilities.

## License
MIT — see LICENSE



