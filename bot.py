import os
import random
import string
from urllib import response
import aiohttp  # type: ignore
import discord  # type: ignore
from discord.ext import commands  # type: ignore
from discord import app_commands  # type: ignore
import psutil  # type: ignore
import asyncio
import io
import subprocess
import datetime
import tempfile
from pathlib import Path
import base64
import json
import urllib.parse
from urllib.parse import urlparse
from typing import Optional
import html
import pytz  # type: ignore
import time
import platform
import shutil
import urllib.request
import hashlib
from cryptography.fernet import Fernet  # type: ignore

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

habitslist = []  # (LEGACY) no longer used for executing loops; maintained for compatibility with existing code
# New habits system: each habit is a cancelable asynchronous task.
# Key: we use the message as identifier (you can change it to a UUID if you want repeated messages).
habit_tasks: dict[str, dict] = {}

def _derive_fernet_key(passphrase: str) -> bytes:
    """Derives a valid Fernet key (base64 urlsafe 32 bytes) from any passphrase.
    This allows the user to use 'any word'. (SHA-256 -> 32 bytes -> base64)"""
    h = hashlib.sha256(passphrase.encode()).digest()  # 32 bytes
    return base64.urlsafe_b64encode(h)

def _normalize_fernet_key(key: str) -> bytes:
    """Accepts both an already encoded Fernet key (44 chars approx) and a free passphrase."""
    raw = key.strip()
    # Try to use it directly
    try:
        Fernet(raw)
        return raw.encode()
    except Exception:
        # Derive from passphrase
        return _derive_fernet_key(raw)

# —— Nextcloud Output ——
def _get_base_nextcloud_dir() -> Path:
    # 1) Allow override by environment variable
    env = os.getenv("NEXTCLOUD_DIR") or os.getenv("NEXTCLOUD_PATH")
    if env:
        return Path(env)
    # 2) Path provided by user as candidate
    provided = Path("/mnt/ssd/nextcloud/pablo/files/Bot")
    candidates = [provided]
    # 3) Common heuristics (Windows/Linux)
    candidates += [
        Path.home() / "Nextcloud",
        Path.home() / "NextCloud",
        Path.home() / "OneDrive" / "Documents" / "NextCloud",
        Path.home() / "Documents" / "Nextcloud",
    ]
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    return Path.cwd()

def get_output_dir(kind: str | None = None) -> Path:
    """Gets/creates the output directory.
    kind: 'screenshots' | 'pdfs' | 'videos' for specific subfolders.
    """
    base = _get_base_nextcloud_dir()
    name_map = {
        "screenshots": "Screenshots",
        "pdfs": "Merged pdfs",
        "videos": "Merged videos",
    }
    target = base
    if kind:
        target = base / name_map.get(kind, kind)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except Exception:
        # If we can't create there, use cwd as fallback
        fallback = Path.cwd() / (name_map.get(kind, kind or "output") if kind else "output")
        fallback.mkdir(parents=True, exist_ok=True)
        target = fallback
    return target

def unique_path(directory: Path, filename: str) -> Path:
    p = directory / filename
    if not p.exists():
        return p
    stem = p.stem
    suffix = p.suffix
    for i in range(1, 1000):
        candidate = directory / f"{stem}-{i:03d}{suffix}"
        if not candidate.exists():
            return candidate
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return directory / f"{stem}-{ts}{suffix}"

@bot.tree.command(name="help", description="Shows the list of commands")
async def help(interaction: discord.Interaction):
    list = (
        "Available commands:\n"
        "- /help: Shows the list of commands\n"
        "- /example: Greets you\n"
        "- /stats: Shows system statistics\n"
        "- /reboot: Restarts the Raspberry Pi\n"
        "- /shutdown: Shuts down the Raspberry Pi\n"
        "- /update: Updates the system (apt)\n"
        "- /vpnstatus: Shows WireGuard VPN status\n"
        "- /netdevices: Lists devices connected to the network\n"
        "- /ping <ip>: Performs a ping (4 attempts)\n"
        "- /webping <url> [times]: Checks HTTP URL and latency\n"
        "- /whois <domain>: WHOIS information for domain\n"
        "- /speedtest: Speed test (simple)\n"
        "- /shorten <url>: Shortens a URL\n"
        "- /screenshotweb <url>: Web page screenshot\n"
        "- /qr <url>: Generates a QR code\n"
        "- /passw <chars>: Generates a random password\n"
        "- /mergepdf <file1..file5>: Merges multiple PDFs\n"
        "- /mergevid <file1..file5>: Merges multiple videos into MP4\n"
        "- /remind <min> <message>: Single reminder\n"
        "- /habit <min> <message>: Recurring reminder (cancelable)\n"
        "- /listhabit: Lists active habits\n"
        "- /deletehabit <message>: Deletes a habit\n"
        "- /translate <text> <language>: Translates text\n"
        "- /definition <word> [language]: Definition of a word\n"
        "- /weather <place>: Current weather for a city\n"
        "- /timezone <zone>: Time in a timezone\n"
        "- /roll <dice> [sides]: Roll dice\n"
        "- /encrypt <message> <key|passphrase>: Encrypts (Fernet; passphrase accepted)\n"
        "- /decrypt <text> <key|passphrase>: Decrypts\n"
        "- /hash <message> [alg]: Hash (sha256/sha512/blake2b/blake2s/md5)\n"
        "- /restart: Restarts the bot (systemd)\n"
        "- /execute <command>: Executes a command on the host"
    )
    await interaction.response.send_message(list)

@bot.tree.command(name="example", description="Greets you")
async def example(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")


@bot.tree.command(name="stats",description="Shows statistics")
async def stats(interaction: discord.Interaction):
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    tmp = psutil.disk_usage('/tmp')
    # uptime in seconds since boot
    boot = psutil.boot_time()
    elapsed = int(time.time() - boot)
    days = elapsed // 86400
    rem = elapsed % 86400
    hours = rem // 3600
    rem %= 3600
    minutes = rem // 60
    seconds = rem % 60
    uptime_str = f"{days:02d}:{hours:02d}:{minutes:02d}:{seconds:02d}"
    stats_msg = (
        f"**Raspberry Pi Statistics:**\n"
        f"CPU: {cpu}%\n"
        f"RAM: {mem.percent}% ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)\n"
        f"Disk: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)\n"
        f"TMP: {tmp.percent}% ({tmp.used // (1024**3)}GB / {tmp.total // (1024**3)}GB)\n"
        f"Uptime (DD:HH:MM:SS): {uptime_str}"
    )
    await interaction.response.send_message(stats_msg)

@bot.tree.command(name="reboot", description="Restarts the Raspberry Pi")
async def reboot(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Restarting the Raspberry Pi...", ephemeral=True)
    # Run reboot in background to avoid blocking
    asyncio.create_task(asyncio.to_thread(os.system, "sudo reboot"))

@bot.tree.command(name="shutdown", description="Shuts down the Raspberry Pi")
async def shutdown(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Shutting down the Raspberry Pi...", ephemeral=True)
    asyncio.create_task(asyncio.to_thread(os.system, "sudo shutdown now"))

@bot.tree.command(name="update", description="Updates the system")
async def update(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Updating the system...", ephemeral=True)
    
    async def _run_update():
        code = await asyncio.to_thread(os.system, "sudo apt update && sudo apt upgrade -y")
        try:
            await interaction.followup.send(f"Update finished (code {code}).", ephemeral=True)
        except Exception:
            pass
    
    asyncio.create_task(_run_update())

@bot.tree.command(name="vpnstatus", description="Shows VPN status")
async def vpnstatus(interaction: discord.Interaction):
    await interaction.response.defer()
    vpn_status = await asyncio.to_thread(lambda: os.popen("sudo wg show").read())
    await interaction.followup.send(f"VPN Status:\n{vpn_status}")

@bot.tree.command(name="netdevices", description="Lists devices connected to the network")
async def netdevices(interaction: discord.Interaction):
    await interaction.response.defer()
    net_devices = await asyncio.to_thread(lambda: os.popen("ip neigh").read())
    await interaction.followup.send(f"Devices connected to the network:\n{net_devices}")



@bot.tree.command(name="ping", description="Performs a ping to an IP address")
async def ping(interaction: discord.Interaction, ip_address: str):
    await interaction.response.defer()
    # Use appropriate flag for Windows (-n) vs Linux (-c)
    flag = "-n" if platform.system().lower().startswith("win") else "-c"
    result = await asyncio.to_thread(lambda: os.popen(f"ping {flag} 4 {ip_address}").read())
    await interaction.followup.send(f"Ping result to {ip_address}:\n{result}")

@bot.tree.command(name="shorten", description="Shortens a URL")
async def shorten(interaction: discord.Interaction, url:str):
    await interaction.response.defer()
    result = await asyncio.to_thread(lambda: os.popen(f'curl -s "https://is.gd/create.php?format=simple&url={url}"').read())
    await interaction.followup.send(f"Shortened URL:\n{result}")


@bot.tree.command(name="whois", description="Searches domain information")
async def whois(interaction: discord.Interaction, domain: str):
    await interaction.response.defer()
    result = await asyncio.to_thread(lambda: os.popen(f"whois {domain}").read())
    await interaction.followup.send(f"Information for {domain}:\n```\n{result}\n```")

@bot.tree.command(name="speedtest", description="Performs an internet speed test")
async def speedtest(interaction: discord.Interaction):
    await interaction.response.defer()
    result = await asyncio.to_thread(lambda: os.popen("speedtest-cli --secure --simple").read())
    await interaction.followup.send(f"Speed test result:\n```\n{result}\n```")

@bot.tree.command(name="webping", description="Checks a URL (HTTP) and measures latency")
@app_commands.describe(url="URL to check (http/https)", times="Number of attempts (1-5, default 3)")
async def webping(interaction: discord.Interaction, url: str, times: Optional[int] = 3):
    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    tries = 3 if not isinstance(times, int) else max(1, min(5, times))
    await interaction.response.defer()

    latencies: list[float] = []
    statuses: list[int] = []
    errors: list[str] = []

    timeout = aiohttp.ClientTimeout(total=15)
    headers = {"User-Agent": "utilsbot/1.0 (+https://discord)"}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        for i in range(tries):
            t0 = time.perf_counter()
            try:
                async with session.get(url, allow_redirects=True, ssl=False) as resp:
                    _ = await resp.read()  # read to measure properly
                    dt = (time.perf_counter() - t0) * 1000.0
                    latencies.append(dt)
                    statuses.append(resp.status)
            except Exception as e:
                dt = (time.perf_counter() - t0) * 1000.0
                latencies.append(dt)
                errors.append(str(e))

    ok = [s for s in statuses if 200 <= s < 400]
    avg = sum(latencies) / len(latencies) if latencies else 0.0
    best = min(latencies) if latencies else 0.0
    worst = max(latencies) if latencies else 0.0

    status_line = (
        f"HTTP OK ({len(ok)}/{tries}) " + (f"Last: {statuses[-1]}" if statuses else ("Error" if errors else ""))
    )
    msg = (
        f"Web ping to {url}:\n"
        f"{status_line}\n"
        f"Latency ms -> avg: {avg:.1f}, best: {best:.1f}, worst: {worst:.1f}"
    )

    if errors and len(errors) == tries:
        msg += f"\nError: {errors[-1][:140]}"

    await interaction.followup.send(msg)

@bot.tree.command(name="screenshotweb", description="Takes a screenshot of a web page")
async def screenshotweb(interaction: discord.Interaction, url: str):
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    await interaction.response.defer()

    import urllib.request

    screenshot_url = f"https://image.thum.io/get/{url}"

    try:
        image_bytes = await asyncio.to_thread(
            lambda: urllib.request.urlopen(screenshot_url, timeout=20).read()
        )
    except Exception as e:
        await interaction.followup.send(f"Could not get screenshot: {e}")
        return

    # Save to Nextcloud with unique name
    out_dir = get_output_dir("screenshots")
    parsed = urlparse(url)
    host = parsed.netloc or "screenshot"
    target = unique_path(out_dir, f"{host}.png")
    try:
        target.write_bytes(image_bytes)
    except Exception:
        pass

    file = discord.File(fp=io.BytesIO(image_bytes), filename=target.name)
    await interaction.followup.send(content=f"Screenshot of {url}:", file=file)


@bot.tree.command(name="qr", description="Generates a QR code from a URL")
async def qr(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?data={url}&size=200x200"

    try:
        image_bytes = await asyncio.to_thread(
            lambda: urllib.request.urlopen(qr_url, timeout=20).read()
        )
        file = discord.File(fp=io.BytesIO(image_bytes), filename="qr.png")
        await interaction.followup.send(content=f"QR code for {url}:", file=file)
    except Exception as e:
        await interaction.followup.send(f"Could not generate QR code: {e}")


@bot.tree.command(name="passw", description="Generates a password")
async def passw(interaction: discord.Interaction, chars: int):
    await interaction.response.defer()
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=chars))
    await interaction.followup.send(f"Here's your password: {password}")

@bot.tree.command(name="mergepdf", description="Merges multiple attached PDFs into one")
@app_commands.describe(
    file1="PDF 1 (required)",
    file2="PDF 2 (optional)",
    file3="PDF 3 (optional)",
    file4="PDF 4 (optional)",
    file5="PDF 5 (optional)",
)
async def mergepdf(
    interaction: discord.Interaction,
    file1: discord.Attachment,
    file2: Optional[discord.Attachment] = None,
    file3: Optional[discord.Attachment] = None,
    file4: Optional[discord.Attachment] = None,
    file5: Optional[discord.Attachment] = None,
):
    await interaction.response.defer()

    attachments = [f for f in [file1, file2, file3, file4, file5] if f is not None]
    if len(attachments) < 2:
        await interaction.followup.send("Attach at least 2 PDFs.", ephemeral=True)
        return

    # Basic type validation
    for a in attachments:
        name = (a.filename or "").lower()
        ctype = (a.content_type or "").lower()
        if not (name.endswith(".pdf") or "pdf" in ctype):
            await interaction.followup.send(f"'{a.filename}' doesn't appear to be a PDF.", ephemeral=True)
            return

    try:
        from pypdf import PdfReader, PdfWriter  # type: ignore
    except Exception:
        await interaction.followup.send(
            "pypdf library is missing. Install it with: pip install pypdf",
            ephemeral=True,
        )
        return

    # Download and merge
    writer = PdfWriter()
    try:
        for a in attachments:
            data = await a.read()
            reader = PdfReader(io.BytesIO(data))
            # Handle encrypted PDFs without password
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    await interaction.followup.send(
                        f"PDF '{a.filename}' is protected and cannot be opened.",
                        ephemeral=True,
                    )
                    return
            for page in reader.pages:
                writer.add_page(page)

        buf = io.BytesIO()
        writer.write(buf)
        writer.close()
        buf.seek(0)
    except Exception as e:
        await interaction.followup.send(f"Could not merge PDFs: {e}", ephemeral=True)
        return

    data = buf.getvalue()
    # Save to Nextcloud with unique name
    out_dir = get_output_dir("pdfs")
    merged_path = unique_path(out_dir, "merged.pdf")
    try:
        merged_path.write_bytes(data)
    except Exception:
        pass
    merged_name = merged_path.name
    LIMIT = 24 * 1024 * 1024  # ~24 MiB safe for attachment

    if len(data) <= LIMIT:
        await interaction.followup.send(
            content="Here's your merged PDF:",
            file=discord.File(fp=io.BytesIO(data), filename=merged_name),
        )
        return
    else:
        await interaction.followup.send(
            f"The merged PDF exceeds the attachment limit. Saved as '{merged_name}'.",
            ephemeral=True,
        )


@bot.tree.command(name="mergevid", description="Merges two videos into one")
@app_commands.describe(
    file1="Video 1 (required)",
    file2="Video 2 (optional)",
    file3="Video 3 (optional)",
    file4="Video 4 (optional)",
    file5="Video 5 (optional)",
)
async def mergevid(
    interaction: discord.Interaction,
    file1: discord.Attachment,
    file2: Optional[discord.Attachment] = None,
    file3: Optional[discord.Attachment] = None,
    file4: Optional[discord.Attachment] = None,
    file5: Optional[discord.Attachment] = None,
):
    """Concatenates 2-5 videos into an MP4. First tries "stream copy" and if it fails, re-encodes."""
    await interaction.response.defer()

    attachments = [f for f in [file1, file2, file3, file4, file5] if f is not None]
    if len(attachments) < 2:
        await interaction.followup.send("Attach at least 2 videos.", ephemeral=True)
        return

    # Basic type validation
    video_exts = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".ts")
    for a in attachments:
        name = (a.filename or "").lower()
        ctype = (a.content_type or "").lower()
        if not (name.endswith(video_exts) or ctype.startswith("video/")):
            await interaction.followup.send(
                f"'{a.filename}' doesn't appear to be a video.", ephemeral=True
            )
            return

    # Check ffmpeg available
    async def _check_ffmpeg() -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False

    if not await _check_ffmpeg():
        await interaction.followup.send(
            "ffmpeg is not available on the system. Install it to use /mergevid.",
            ephemeral=True,
        )
        return

    LIMIT = 24 * 1024 * 1024  # ~24 MiB safe for attachment

    # Main flow: download to temp, try concat demuxer (-c copy), if it fails re-encode.
    try:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            local_files: list[Path] = []

            # Download attachments to temporary files
            for idx, att in enumerate(attachments):
                data = await att.read()
                suffix = Path(att.filename or f"vid{idx}.mp4").suffix or ".mp4"
                p = td_path / f"in_{idx:02d}{suffix}"
                p.write_bytes(data)
                local_files.append(p)

            out_path = td_path / "merged.mp4"

            # 1) Quick attempt: concat demuxer with stream copy
            list_file = td_path / "inputs.txt"

            def _quote_for_concat(path: Path) -> str:
                s = str(path)
                # Escape single quotes according to concat demuxer
                s = s.replace("'", "'\\''")
                return f"file '{s}'"

            list_file.write_text("\n".join(_quote_for_concat(p) for p in local_files), encoding="utf-8")

            proc1 = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(out_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, err1 = await proc1.communicate()

            if proc1.returncode != 0 or not out_path.exists():
                # 2) Fallback: re-encode with concat filter
                # Detect if all have audio
                async def _has_audio(p: Path) -> bool:
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            "ffprobe", "-v", "error",
                            "-select_streams", "a:0",
                            "-show_entries", "stream=codec_type",
                            "-of", "csv=p=0",
                            str(p),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        out, _ = await proc.communicate()
                        return proc.returncode == 0 and (out.decode().strip() != "")
                    except Exception:
                        return False

                audio_flags = await asyncio.gather(*(_has_audio(p) for p in local_files))
                all_have_audio = all(audio_flags)

                # Build ffmpeg command with inputs
                args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
                for p in local_files:
                    args += ["-i", str(p)]

                n = len(local_files)
                if all_have_audio and n > 0:
                    v_in = "".join(f"[{i}:v:0]" for i in range(n))
                    a_in = "".join(f"[{i}:a:0]" for i in range(n))
                    filter_str = f"{v_in}{a_in}concat=n={n}:v=1:a=1[v][a]"
                    args += [
                        "-filter_complex", filter_str,
                        "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "128k",
                        str(out_path),
                    ]
                else:
                    # No audio (or mixed). Concatenate video only and silence audio.
                    v_in = "".join(f"[{i}:v:0]" for i in range(n))
                    filter_str = f"{v_in}concat=n={n}:v=1:a=0[v]"
                    args += [
                        "-filter_complex", filter_str,
                        "-map", "[v]",
                        "-an",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        str(out_path),
                    ]

                proc2 = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, err2 = await proc2.communicate()
                if proc2.returncode != 0 or not out_path.exists():
                    # Definitive failure
                    tail = (err2 or err1 or b"").decode(errors="ignore")
                    tail = tail[-600:]
                    await interaction.followup.send(
                        "Could not merge videos. Technical detail:\n" + tail,
                        ephemeral=True,
                    )
                    return

            # Send result if it doesn't exceed the limit
            out_bytes = out_path.read_bytes()
            # Save to Nextcloud with unique name
            out_dir = get_output_dir("videos")
            final_path = unique_path(out_dir, "merged.mp4")
            try:
                shutil.copy2(out_path, final_path)
            except Exception:
                try:
                    final_path.write_bytes(out_bytes)
                except Exception:
                    pass
            if len(out_bytes) > LIMIT:
                await interaction.followup.send(
                    f"The resulting video exceeds the bot's attachment limit. Saved as '{final_path.name}'.",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                content="Here's your merged video:",
                file=discord.File(fp=io.BytesIO(out_bytes), filename=final_path.name),
            )
            return
    except Exception as e:
        await interaction.followup.send(f"An error occurred while merging videos: {e}", ephemeral=True)
        return




@bot.tree.command(name="remind", description="Creates a reminder")
@app_commands.describe(
    time="Time until reminder (in minutes)",
    message="Reminder message"
)
async def remind(
    interaction: discord.Interaction,
    time: int,
    message: str
):
    await interaction.response.defer()

    if time < 1:
        await interaction.followup.send("Time must be at least 1 minute.", ephemeral=True)
        return

    await interaction.followup.send(f"Reminder set for {time} minutes from now.")

    await asyncio.sleep(time * 60)
    await interaction.followup.send(f"Reminder! {message}")


@bot.tree.command(name="habit", description="Creates a recurring reminder")
@app_commands.describe(
    time="Time between repetitions (in minutes)",
    message="Reminder message"
)
async def habit(
    interaction: discord.Interaction,
    time: int,
    message: str
):
    await interaction.response.defer()

    if time < 1:
        await interaction.followup.send("Time must be at least 1 minute.", ephemeral=True)
        return
    # If a habit with the same message already exists, replace it
    if message in habit_tasks:
        # Cancel the previous one
        old_task = habit_tasks[message]["task"]
        old_task.cancel()
        await interaction.followup.send(f"Existing habit updated: every {time} minutes -> {message}")
    else:
        await interaction.followup.send(f"Habit created: every {time} minutes -> {message}")

    interval_minutes = time

    async def _habit_loop(msg: str, interval: int):
        try:
            # Initial wait before first reminder (optional). If you want to send one immediately, remove the first sleep.
            while True:
                await asyncio.sleep(interval * 60)
                try:
                    await interaction.followup.send(f"Reminder! {msg}")
                except Exception:
                    pass
        except asyncio.CancelledError:
            # Cleanup when cancelled
            pass
        finally:
            # Remove from registry if it still points to this task
            current = habit_tasks.get(msg)
            if current and current.get("task") == asyncio.current_task():
                habit_tasks.pop(msg, None)

    task = asyncio.create_task(_habit_loop(message, interval_minutes))
    habit_tasks[message] = {"interval": interval_minutes, "task": task}


@bot.tree.command(name="listhabit", description="Lists habits")
async def listhabit(interaction: discord.Interaction):
    await interaction.response.defer()

    if not habit_tasks:
        await interaction.followup.send("No habits configured.")
        return
    habit_messages = [f"- Every {data['interval']} minutes: {msg}" for msg, data in habit_tasks.items()]
    await interaction.followup.send("Habit list:\n" + "\n".join(habit_messages))

@bot.tree.command(name="deletehabit", description="Deletes a habit")
@app_commands.describe(
    message="Message of habit to delete"
)
async def deletehabit(
    interaction: discord.Interaction,
    message: str
):
    await interaction.response.defer()
    data = habit_tasks.get(message)
    if not data:
        await interaction.followup.send("Habit not found.", ephemeral=True)
        return
    task: asyncio.Task = data["task"]
    task.cancel()
    # Deletion is handled by the loop's finally, but clean up just in case
    habit_tasks.pop(message, None)
    await interaction.followup.send(f"Habit deleted: {message}")
    return




@bot.tree.command(name="translate", description="Translates text to another language")
@app_commands.describe(
    text="Text to translate",
    target_language="Language to translate to"
)
async def translate(
    interaction: discord.Interaction,
    text: str,
    target_language: str
):
    await interaction.response.defer()

    # Normalize target language and translate using MyMemory API

    lang_map = {
        "es": "es", "español": "es", "spanish": "es",
        "en": "en", "ingles": "en", "inglés": "en", "english": "en",
        "fr": "fr", "frances": "fr", "francés": "fr", "french": "fr",
        "de": "de", "aleman": "de", "alemán": "de", "german": "de",
        "it": "it", "italiano": "it", "italian": "it",
        "pt": "pt", "portugues": "pt", "portugués": "pt", "portuguese": "pt",
        "ru": "ru", "ruso": "ru", "russian": "ru",
        "ja": "ja", "japones": "ja", "japonés": "ja", "japanese": "ja",
        "zh": "zh", "chino": "zh", "chinese": "zh",
        "ar": "ar", "arabe": "ar", "árabe": "ar", "arabic": "ar",
        "nl": "nl", "holandes": "nl", "holandés": "nl", "dutch": "nl",
        "pl": "pl", "polaco": "pl", "polish": "pl",
        "sv": "sv", "sueco": "sv", "swedish": "sv",
        "tr": "tr", "turco": "tr", "turkish": "tr",
        "ko": "ko", "coreano": "ko", "korean": "ko",
        "cs": "cs", "checo": "cs", "czech": "cs",
        "ca": "ca", "catalan": "ca", "catalán": "ca",
        "gl": "gl", "gallego": "gl",
        "eu": "eu", "euskera": "eu", "basque": "eu",
    }

    norm = (target_language or "").strip().lower()
    target_code = lang_map.get(norm)
    if not target_code:
        candidate = norm.replace("_", "-")
        if candidate.isalpha() or ("-" in candidate and candidate.replace("-", "").isalpha()):
            target_code = candidate[:5]  # accept codes like pt-br
        else:
            target_code = "es"

    try:
        q = urllib.parse.quote_plus(text)
        # Use 'es' as source language instead of 'auto' to avoid API error
        url = f"https://api.mymemory.translated.net/get?q={q}&langpair=es|{target_code}"
        def _fetch():
            req = urllib.request.Request(url, headers={
                "User-Agent": "utilsbot/1.0 (+https://discord)"
            })
            return urllib.request.urlopen(req, timeout=20).read()
        raw = await asyncio.to_thread(_fetch)
        payload = json.loads(raw.decode("utf-8", errors="ignore"))
        status = payload.get("responseStatus", 200)
        translated = ""
        if status == 200:
            translated = (payload.get("responseData") or {}).get("translatedText") or ""
            if not translated:
                for m in payload.get("matches") or []:
                    if m.get("translation"):
                        translated = m["translation"]
                        break
        if translated and translated.lower() != text.lower():
            text = html.unescape(translated)
        elif status != 200:
            # If API fails, try with English as source
            try:
                url2 = f"https://api.mymemory.translated.net/get?q={q}&langpair=en|{target_code}"
                req2 = urllib.request.Request(url2, headers={
                    "User-Agent": "utilsbot/1.0 (+https://discord)"
                })
                raw2 = await asyncio.to_thread(lambda: urllib.request.urlopen(req2, timeout=20).read())
                payload2 = json.loads(raw2.decode("utf-8", errors="ignore"))
                if payload2.get("responseStatus", 200) == 200:
                    alt_translated = (payload2.get("responseData") or {}).get("translatedText") or ""
                    if alt_translated and alt_translated.lower() != text.lower():
                        text = html.unescape(alt_translated)
            except Exception:
                pass
    except Exception as e:
        await interaction.followup.send(f"Could not translate: {e}", ephemeral=True)
        return

    translated_text = f"Text translated to {target_language}: {text}"

    await interaction.followup.send(translated_text)


@bot.tree.command(name="definition", description="Searches for the definition of a word")
@app_commands.describe(
    word="Word to search",
    language="Language to search definition in (optional, default is Spanish)"
)
async def definition(
    interaction: discord.Interaction,
    word: str,
    language: str = "es"
):
    await interaction.response.defer()

    # Normalize the language and query the public DictionaryAPI
    lang_aliases = {
        "es": "es", "español": "es", "spanish": "es",
        "en": "en", "ingles": "en", "inglés": "en", "english": "en",
        "fr": "fr", "frances": "fr", "francés": "fr", "french": "fr",
        "de": "de", "aleman": "de", "alemán": "de", "german": "de",
        "it": "it", "italiano": "it", "italian": "it",
        "pt": "pt-BR", "pt-br": "pt-BR", "portugues": "pt-BR", "portugués": "pt-BR", "portuguese": "pt-BR",
        "ru": "ru", "ruso": "ru", "russian": "ru",
        "ja": "ja", "japones": "ja", "japonés": "ja", "japanese": "ja",
        "ko": "ko", "coreano": "ko", "korean": "ko",
        "ar": "ar", "arabe": "ar", "árabe": "ar", "arabic": "ar",
        "tr": "tr", "turco": "tr", "turkish": "tr",
        "hi": "hi", "hindi": "hi",
    }
    norm_lang = (language or "es").strip().lower()
    lang_code = lang_aliases.get(norm_lang, norm_lang if norm_lang else "es")
    if lang_code in ("pt", "pt_br"):
        lang_code = "pt-BR"

    term = (word or "").strip()
    if not term:
        await interaction.followup.send("Provide a valid word.")
        return

    try:
        q = urllib.parse.quote(term)
        url = f"https://api.dictionaryapi.dev/api/v2/entries/{lang_code}/{q}"
        def _fetch_def():
            req = urllib.request.Request(url, headers={
                "User-Agent": "utilsbot/1.0 (+https://discord)"
            })
            return urllib.request.urlopen(req, timeout=20).read()
        raw = await asyncio.to_thread(_fetch_def)
        data = json.loads(raw.decode("utf-8", errors="ignore"))

        definitions = []
        if isinstance(data, list):
            for entry in data:
                for meaning in entry.get("meanings", []):
                    pos = meaning.get("partOfSpeech") or ""
                    for d in meaning.get("definitions", []):
                        txt = d.get("definition")
                        if txt:
                            if pos:
                                definitions.append(f"- ({pos}) {txt}")
                            else:
                                definitions.append(f"- {txt}")
                            if len(definitions) >= 6:
                                break
                    if len(definitions) >= 6:
                        break
                if len(definitions) >= 6:
                    break

        if definitions:
            await interaction.followup.send(
                f"Definition of '{word}' in {language}:\n" + "\n".join(definitions)
            )
        else:
            # Not found message
            msg = data.get("message") if isinstance(data, dict) else None
            await interaction.followup.send(
                msg or f"No definitions found for '{word}' in {language}."
            )
        return
    except Exception as e:
        # Try English as fallback before giving up
        print(f"Definition API error for {lang_code}: {e}")  # Debug log
        if lang_code != "en":
            try:
                q_en = urllib.parse.quote(term)
                url_en = f"https://api.dictionaryapi.dev/api/v2/entries/en/{q_en}"
                req_en = urllib.request.Request(url_en, headers={
                    "User-Agent": "utilsbot/1.0 (+https://discord)"
                })
                raw_en = await asyncio.to_thread(lambda: urllib.request.urlopen(req_en, timeout=20).read())
                data_en = json.loads(raw_en.decode("utf-8", errors="ignore"))
                
                definitions = []
                if isinstance(data_en, list):
                    for entry in data_en:
                        for meaning in entry.get("meanings", []):
                            pos = meaning.get("partOfSpeech") or ""
                            for d in meaning.get("definitions", []):
                                txt = d.get("definition")
                                if txt:
                                    if pos:
                                        definitions.append(f"- ({pos}) {txt}")
                                    else:
                                        definitions.append(f"- {txt}")
                                    if len(definitions) >= 3:
                                        break
                            if len(definitions) >= 3:
                                break
                        if len(definitions) >= 3:
                            break
                
                if definitions:
                    await interaction.followup.send(
                        f"Definition of '{word}' in English (not found in {language}):\n" + "\n".join(definitions)
                    )
                    return
            except Exception as e2:
                print(f"Definition fallback error: {e2}")  # Debug log
                pass
        
        await interaction.followup.send(
            f"Could not get definition. Error: {str(e)[:100]}", ephemeral=True
        )


@bot.tree.command(name="weather", description="Shows current weather for a city (no API key required)")
async def weather(interaction: discord.Interaction, place: str):
    await interaction.response.defer()

    def code_info(code: int | None) -> tuple[str, str]:
        mapping = {
            0: ("Clear", "☀️"),
            1: ("Mostly clear", "🌤️"),
            2: ("Partly cloudy", "⛅"),
            3: ("Cloudy", "☁️"),
            45: ("Fog", "🌫️"),
            48: ("Fog with frost", "🌫️"),
            51: ("Light drizzle", "🌦️"),
            53: ("Moderate drizzle", "🌦️"),
            55: ("Heavy drizzle", "🌧️"),
            56: ("Light freezing drizzle", "🌧️"),
            57: ("Heavy freezing drizzle", "🌧️"),
            61: ("Light rain", "🌧️"),
            63: ("Moderate rain", "🌧️"),
            65: ("Heavy rain", "🌧️"),
            66: ("Light freezing rain", "🌧️"),
            67: ("Heavy freezing rain", "🌧️"),
            71: ("Light snow", "🌨️"),
            73: ("Moderate snow", "🌨️"),
            75: ("Heavy snow", "❄️"),
            77: ("Fine hail", "🌨️"),
            80: ("Light showers", "🌦️"),
            81: ("Moderate showers", "🌦️"),
            82: ("Heavy showers", "🌧️"),
            85: ("Light snow showers", "🌨️"),
            86: ("Heavy snow showers", "❄️"),
            95: ("Thunderstorm", "⛈️"),
            96: ("Thunderstorm with hail", "⛈️"),
            99: ("Heavy thunderstorm with hail", "⛈️"),
        }
        return mapping.get(int(code) if code is not None else -1, ("Weather", "🌡️"))

    try:
        # Geocode the place
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search?" +
            urllib.parse.urlencode({"name": place, "count": 1, "language": "en", "format": "json"})
        )
        geo_bytes = await asyncio.to_thread(lambda: urllib.request.urlopen(geo_url, timeout=15).read())
        geo = json.loads(geo_bytes.decode("utf-8"))
        results = geo.get("results") or []
        if not results:
            await interaction.followup.send("I couldn't find that location.", ephemeral=True)
            return
        g = results[0]
        lat, lon = g["latitude"], g["longitude"]
        loc_name = g.get("name")
        admin1 = g.get("admin1")
        country = g.get("country")

        # Current weather
        current_params = ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "is_day",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
        ])
        fc_url = (
            "https://api.open-meteo.com/v1/forecast?" +
            urllib.parse.urlencode({
                "latitude": lat,
                "longitude": lon,
                "current": current_params,
                "timezone": "auto",
                "windspeed_unit": "kmh",
            })
        )
        fc_bytes = await asyncio.to_thread(lambda: urllib.request.urlopen(fc_url, timeout=15).read())
        data = json.loads(fc_bytes.decode("utf-8"))
        current = data.get("current") or {}

        temp = current.get("temperature_2m")
        app_temp = current.get("apparent_temperature")
        rh = current.get("relative_humidity_2m")
        wind = current.get("wind_speed_10m")
        wind_dir = current.get("wind_direction_10m")
        code = current.get("weather_code")
        desc, emoji = code_info(code)

        header = f"Weather in {loc_name}"
        if admin1:
            header += f", {admin1}"
        if country:
            header += f", {country}"

        msg = f"{header}:\n{emoji} {desc}\n"
        if temp is not None:
            msg += f"Temp: {temp}°C"
            if app_temp is not None:
                msg += f" (feels like {app_temp}°C)"
            msg += "\n"
        if rh is not None:
            msg += f"Humidity: {rh}%\n"
        if wind is not None:
            msg += f"Wind: {wind} km/h"
            if wind_dir is not None:
                msg += f" ({wind_dir}°)"
            msg += "\n"

        await interaction.followup.send(msg)
    except Exception as e:
        await interaction.followup.send(f"I couldn't get the weather: {e}", ephemeral=True)

@bot.tree.command(name="timezone", description="Check time in another timezone")
async def timezone(interaction: discord.Interaction, zone: str):
    await interaction.response.defer()
    try:
        # Get current time in the specified timezone
        tz = pytz.timezone(zone)
        current_time = datetime.datetime.now(tz).strftime("%H:%M:%S")
        await interaction.followup.send(f"Current time in {zone} is {current_time}.")
    except Exception as e:
        await interaction.followup.send(f"I couldn't get the time: {e}", ephemeral=True)

@bot.tree.command(name="restart", description="Restarts the bot")
async def restart(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        service = os.getenv("SERVICE_NAME", "utilsbot.service")
        await asyncio.to_thread(os.system, f"sudo systemctl restart {service}")
        await interaction.followup.send("Restarting the bot...", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"I couldn't restart the bot: {e}", ephemeral=True)

@bot.tree.command(name="execute", description="Executes a command on the Raspberry Pi")
async def execute(interaction: discord.Interaction, command: str):
    await interaction.response.defer()
    try:
        output = await asyncio.to_thread(lambda: subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT))
        await interaction.followup.send(f"Command output:\n```\n{output.decode()}\n```")
    except Exception as e:
        await interaction.followup.send(f"I couldn't execute the command: {e}", ephemeral=True)

@bot.tree.command(name="roll", description="Rolls a dice")
async def roll(interaction: discord.Interaction, dices: int, sides: int = 6):
    await interaction.response.defer()
    results = [random.randint(1, sides) for _ in range(dices)]
    await interaction.followup.send(f"Results of rolling {dices} {sides}-sided dice: {results}")

@bot.tree.command(name="encrypt", description="Encrypts a message")
async def encrypt(interaction: discord.Interaction, message: str, key: str):
    await interaction.response.defer()
    try:
        norm_key = _normalize_fernet_key(key)
        fernet = Fernet(norm_key)
        encrypted = fernet.encrypt(message.encode()).decode()
        # Simplified: always show only the encrypted text; the same passphrase serves to decrypt.
        await interaction.followup.send(f"Encrypted message:\n```\n{encrypted}\n```")
    except Exception as e:
        await interaction.followup.send(f"I couldn't encrypt the message: {e}", ephemeral=True)


@bot.tree.command(name="decrypt", description="Decrypts a message")
async def decrypt(interaction: discord.Interaction, message: str, key: str):
    await interaction.response.defer()
    try:
        norm_key = _normalize_fernet_key(key)
        fernet = Fernet(norm_key)
        decrypted = fernet.decrypt(message.encode()).decode()
        await interaction.followup.send(f"Decrypted message:\n```\n{decrypted}\n```")
    except Exception as e:
        await interaction.followup.send(f"I couldn't decrypt the message: {e}", ephemeral=True)

@bot.tree.command(name="hash", description="Generates a hash of a message (SHA-256 by default)")
async def hash(interaction: discord.Interaction, message: str, algorithm: str = "sha256"):
    await interaction.response.defer()
    try:
        if algorithm == "sha256":
            hash_object = hashlib.sha256(message.encode())
        elif algorithm == "sha512":
            hash_object = hashlib.sha512(message.encode())
        elif algorithm == "blake2b":
            hash_object = hashlib.blake2b(message.encode())
        elif algorithm == "blake2s":
            hash_object = hashlib.blake2s(message.encode())
        elif algorithm == "md5":
            hash_object = hashlib.md5(message.encode())
        else:
            await interaction.followup.send(f"Algorithm not supported: {algorithm}", ephemeral=True)
            return

        hash_hex = hash_object.hexdigest()
        await interaction.followup.send(f"Hash ({algorithm}):\n```\n{hash_hex}\n```")
    except Exception as e:
        await interaction.followup.send(f"I couldn't generate the hash: {e}", ephemeral=True)

@bot.event
async def on_ready():
    # Sync slash commands with Discord on startup
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synchronized: {len(synced)}")
    except Exception as e:
        print(f"Could not synchronize commands: {e}")
    user = getattr(bot, "user", None)
    if user:
        print(f"Connected as {user} (ID: {user.id})")


if __name__ == "__main__":
    # Load .env if python-dotenv is available
    try:
        import dotenv  # type: ignore
        # Look for .env in cwd and next to the script, and support .ENV (Linux is case-sensitive)
        here = Path(__file__).parent
        candidates = [
            Path.cwd() / ".env",
            Path.cwd() / ".ENV",
            here / ".env",
            here / ".ENV",
        ]
        loaded = False
        for p in candidates:
            try:
                if p.exists():
                    dotenv.load_dotenv(dotenv_path=str(p))
                    loaded = True
                    break
            except Exception:
                continue
        if not loaded:
            dotenv.load_dotenv()
    except Exception:
        pass
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Missing DISCORD_TOKEN environment variable.")
    bot.run(token)

