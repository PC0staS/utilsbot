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


@bot.tree.command(name="mergevid", description="Une dos videos en uno")
@app_commands.describe(
    file1="Vídeo 1 (obligatorio)",
    file2="Vídeo 2 (opcional)",
    file3="Vídeo 3 (opcional)",
    file4="Vídeo 4 (opcional)",
    file5="Vídeo 5 (opcional)",
)
async def mergevid(
    interaction: discord.Interaction,
    file1: discord.Attachment,
    file2: Optional[discord.Attachment] = None,
    file3: Optional[discord.Attachment] = None,
    file4: Optional[discord.Attachment] = None,
    file5: Optional[discord.Attachment] = None,
):
    """Concatena 2-5 vídeos en un MP4. Intenta primero "stream copy" y, si falla, re-codifica."""
    await interaction.response.defer()

    attachments = [f for f in [file1, file2, file3, file4, file5] if f is not None]
    if len(attachments) < 2:
        await interaction.followup.send("Adjunta al menos 2 vídeos.", ephemeral=True)
        return

    # Validación básica de tipo
    video_exts = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".ts")
    for a in attachments:
        name = (a.filename or "").lower()
        ctype = (a.content_type or "").lower()
        if not (name.endswith(video_exts) or ctype.startswith("video/")):
            await interaction.followup.send(
                f"'{a.filename}' no parece ser un vídeo.", ephemeral=True
            )
            return

    # Comprobar ffmpeg disponible
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
            "ffmpeg no está disponible en el sistema. Instálalo para usar /mergevid.",
            ephemeral=True,
        )
        return

    LIMIT = 24 * 1024 * 1024  # ~24 MiB seguro para adjuntar

    # Flujo principal: descargar a temp, intentar concat demuxer (-c copy), si falla re-codificar.
    try:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            local_files: list[Path] = []

            # Descargar adjuntos a ficheros temporales
            for idx, att in enumerate(attachments):
                data = await att.read()
                suffix = Path(att.filename or f"vid{idx}.mp4").suffix or ".mp4"
                p = td_path / f"in_{idx:02d}{suffix}"
                p.write_bytes(data)
                local_files.append(p)

            out_path = td_path / "merged.mp4"

            # 1) Intento rápido: demuxer concat con copia de streams
            list_file = td_path / "inputs.txt"

            def _quote_for_concat(path: Path) -> str:
                s = str(path)
                # Escapar comillas simples según concat demuxer
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
                # 2) Fallback: re-codificar con concat filter
                # Detectar si todos tienen audio
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

                # Construir comando ffmpeg con entradas
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
                    # Sin audio (o mezcla dispar). Concatenamos solo vídeo y silenciamos audio.
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
                    # Falla definitiva
                    tail = (err2 or err1 or b"").decode(errors="ignore")
                    tail = tail[-600:]
                    await interaction.followup.send(
                        "No se pudo unir los vídeos. Detalle técnico:\n" + tail,
                        ephemeral=True,
                    )
                    return

            # Enviar resultado si no excede el límite
            out_bytes = out_path.read_bytes()
            # Guardar en Nextcloud con nombre único
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
                    f"El vídeo resultante excede el límite de adjuntos del bot. Se guardó como '{final_path.name}'.",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                content="Aquí tienes tu vídeo unido:",
                file=discord.File(fp=io.BytesIO(out_bytes), filename=final_path.name),
            )
            return
    except Exception as e:
        await interaction.followup.send(f"Ocurrió un error al unir los vídeos: {e}", ephemeral=True)
        return




@bot.tree.command(name="remind", description="Crea un recordatorio")
@app_commands.describe(
    time="Tiempo hasta el recordatorio (en minutos)",
    message="Mensaje del recordatorio"
)
async def remind(
    interaction: discord.Interaction,
    time: int,
    message: str
):
    await interaction.response.defer()

    if time < 1:
        await interaction.followup.send("El tiempo debe ser al menos 1 minuto.", ephemeral=True)
        return

    await interaction.followup.send(f"Recordatorio configurado para dentro de {time} minutos.")

    await asyncio.sleep(time * 60)
    await interaction.followup.send(f"¡Recordatorio! {message}")


@bot.tree.command(name="habit", description="Crea un recordatorio recurrente")
@app_commands.describe(
    time="Tiempo entre repeticiones (en minutos)",
    message="Mensaje del recordatorio"
)
async def habit(
    interaction: discord.Interaction,
    time: int,
    message: str
):
    await interaction.response.defer()

    if time < 1:
        await interaction.followup.send("El tiempo debe ser al menos 1 minuto.", ephemeral=True)
        return
    # Si ya existe un habit con el mismo mensaje, lo reemplazamos
    if message in habit_tasks:
        # Cancelar el anterior
        old_task = habit_tasks[message]["task"]
        old_task.cancel()
        await interaction.followup.send(f"Habit existente actualizado: cada {time} minutos -> {message}")
    else:
        await interaction.followup.send(f"Habit creado: cada {time} minutos -> {message}")

    interval_minutes = time

    async def _habit_loop(msg: str, interval: int):
        try:
            # Espera inicial antes del primer recordatorio (opcional). Si quieres enviar uno inmediato, quita la primera sleep.
            while True:
                await asyncio.sleep(interval * 60)
                try:
                    await interaction.followup.send(f"¡Recordatorio! {msg}")
                except Exception:
                    pass
        except asyncio.CancelledError:
            # Limpieza al cancelar
            pass
        finally:
            # Eliminar de registro si sigue apuntando a esta tarea
            current = habit_tasks.get(msg)
            if current and current.get("task") == asyncio.current_task():
                habit_tasks.pop(msg, None)

    task = asyncio.create_task(_habit_loop(message, interval_minutes))
    habit_tasks[message] = {"interval": interval_minutes, "task": task}


@bot.tree.command(name="listhabit", description="Lista habits")
async def listhabit(interaction: discord.Interaction):
    await interaction.response.defer()

    if not habit_tasks:
        await interaction.followup.send("No hay habits configurados.")
        return
    habit_messages = [f"- Cada {data['interval']} minutos: {msg}" for msg, data in habit_tasks.items()]
    await interaction.followup.send("Lista de habits:\n" + "\n".join(habit_messages))

@bot.tree.command(name="deletehabit", description="Elimina un habit")
@app_commands.describe(
    message="Mensaje del habit a eliminar"
)
async def deletehabit(
    interaction: discord.Interaction,
    message: str
):
    await interaction.response.defer()
    data = habit_tasks.get(message)
    if not data:
        await interaction.followup.send("Habit no encontrado.", ephemeral=True)
        return
    task: asyncio.Task = data["task"]
    task.cancel()
    # Eliminación la maneja el finally del loop, pero limpiamos por si acaso
    habit_tasks.pop(message, None)
    await interaction.followup.send(f"Habit eliminado: {message}")
    return




@bot.tree.command(name="translate", description="Traduce un texto a otro idioma")
@app_commands.describe(
    text="Texto a traducir",
    target_language="Idioma al que traducir"
)
async def translate(
    interaction: discord.Interaction,
    text: str,
    target_language: str
):
    await interaction.response.defer()

    # Normaliza idioma objetivo y traduce usando MyMemory API

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
            target_code = candidate[:5]  # acepta códigos como pt-br
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
        await interaction.followup.send(f"No se pudo traducir: {e}", ephemeral=True)
        return

    translated_text = f"Texto traducido a {target_language}: {text}"

    await interaction.followup.send(translated_text)


@bot.tree.command(name="definition", description="Busca la definición de una palabra")
@app_commands.describe(
    word="Palabra a buscar",
    language="Idioma en el que buscar la definición (opcional, por defecto es español)"
)
async def definition(
    interaction: discord.Interaction,
    word: str,
    language: str = "es"
):
    await interaction.response.defer()

    # Normaliza el idioma y consulta la API pública de DictionaryAPI
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
        await interaction.followup.send("Proporciona una palabra válida.")
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
                f"Definición de '{word}' en {language}:\n" + "\n".join(definitions)
            )
        else:
            # Mensaje de no encontrado
            msg = data.get("message") if isinstance(data, dict) else None
            await interaction.followup.send(
                msg or f"No se encontraron definiciones para '{word}' en {language}."
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
                        f"Definición de '{word}' en inglés (no encontrada en {language}):\n" + "\n".join(definitions)
                    )
                    return
            except Exception as e2:
                print(f"Definition fallback error: {e2}")  # Debug log
                pass
        
        await interaction.followup.send(
            f"No se pudo obtener la definición. Error: {str(e)[:100]}", ephemeral=True
        )


@bot.tree.command(name="weather", description="Muestra el tiempo actual de una ciudad (sin API key)")
async def weather(interaction: discord.Interaction, lugar: str):
    await interaction.response.defer()

    def code_info(code: int | None) -> tuple[str, str]:
        mapping = {
            0: ("Despejado", "☀️"),
            1: ("Mayormente despejado", "🌤️"),
            2: ("Parcialmente nublado", "⛅"),
            3: ("Nublado", "☁️"),
            45: ("Niebla", "🌫️"),
            48: ("Niebla con escarcha", "🌫️"),
            51: ("Llovizna ligera", "🌦️"),
            53: ("Llovizna moderada", "🌦️"),
            55: ("Llovizna intensa", "🌧️"),
            56: ("Llovizna helada ligera", "🌧️"),
            57: ("Llovizna helada intensa", "🌧️"),
            61: ("Lluvia ligera", "🌧️"),
            63: ("Lluvia moderada", "🌧️"),
            65: ("Lluvia intensa", "🌧️"),
            66: ("Lluvia helada ligera", "🌧️"),
            67: ("Lluvia helada intensa", "🌧️"),
            71: ("Nieve ligera", "🌨️"),
            73: ("Nieve moderada", "🌨️"),
            75: ("Nieve intensa", "❄️"),
            77: ("Granizo fino", "🌨️"),
            80: ("Chubascos ligeros", "🌦️"),
            81: ("Chubascos moderados", "🌦️"),
            82: ("Chubascos fuertes", "🌧️"),
            85: ("Chubascos de nieve ligeros", "🌨️"),
            86: ("Chubascos de nieve fuertes", "❄️"),
            95: ("Tormenta", "⛈️"),
            96: ("Tormenta con granizo", "⛈️"),
            99: ("Tormenta fuerte con granizo", "⛈️"),
        }
        return mapping.get(int(code) if code is not None else -1, ("Tiempo", "🌡️"))

    try:
        # Geocodificar el lugar
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search?" +
            urllib.parse.urlencode({"name": lugar, "count": 1, "language": "es", "format": "json"})
        )
        geo_bytes = await asyncio.to_thread(lambda: urllib.request.urlopen(geo_url, timeout=15).read())
        geo = json.loads(geo_bytes.decode("utf-8"))
        results = geo.get("results") or []
        if not results:
            await interaction.followup.send("No encontré esa ubicación.", ephemeral=True)
            return
        g = results[0]
        lat, lon = g["latitude"], g["longitude"]
        loc_name = g.get("name")
        admin1 = g.get("admin1")
        country = g.get("country")

        # Tiempo actual
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

        header = f"Tiempo en {loc_name}"
        if admin1:
            header += f", {admin1}"
        if country:
            header += f", {country}"

        msg = f"{header}:\n{emoji} {desc}\n"
        if temp is not None:
            msg += f"Temp: {temp}°C"
            if app_temp is not None:
                msg += f" (sensación {app_temp}°C)"
            msg += "\n"
        if rh is not None:
            msg += f"Humedad: {rh}%\n"
        if wind is not None:
            msg += f"Viento: {wind} km/h"
            if wind_dir is not None:
                msg += f" ({wind_dir}°)"
            msg += "\n"

        await interaction.followup.send(msg)
    except Exception as e:
        await interaction.followup.send(f"No pude obtener el clima: {e}", ephemeral=True)

@bot.tree.command(name="timezone", description="Consulta la hora en otra zona horaria")
async def timezone(interaction: discord.Interaction, zona: str):
    await interaction.response.defer()
    try:
        # Obtener la hora actual en la zona horaria especificada
        tz = pytz.timezone(zona)
        hora_actual = datetime.datetime.now(tz).strftime("%H:%M:%S")
        await interaction.followup.send(f"La hora actual en {zona} es {hora_actual}.")
    except Exception as e:
        await interaction.followup.send(f"No pude obtener la hora: {e}", ephemeral=True)

@bot.tree.command(name="restart", description="Reincia el bot")
async def restart(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        service = os.getenv("SERVICE_NAME", "utilsbot.service")
        await asyncio.to_thread(os.system, f"sudo systemctl restart {service}")
        await interaction.followup.send("Reiniciando el bot...", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"No pude reiniciar el bot: {e}", ephemeral=True)

@bot.tree.command(name="execute", description="Ejecuta un comando en la Raspberry Pi")
async def execute(interaction: discord.Interaction, command: str):
    await interaction.response.defer()
    try:
        output = await asyncio.to_thread(lambda: subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT))
        await interaction.followup.send(f"Salida del comando:\n```\n{output.decode()}\n```")
    except Exception as e:
        await interaction.followup.send(f"No pude ejecutar el comando: {e}", ephemeral=True)

@bot.tree.command(name="roll", description="Rolls a dice")
async def roll(interaction: discord.Interaction, dices: int, sides: int = 6):
    await interaction.response.defer()
    results = [random.randint(1, sides) for _ in range(dices)]
    await interaction.followup.send(f"Resultados de la tirada de {dices} dados de {sides} caras: {results}")

@bot.tree.command(name="encrypt", description="Encripta un mensaje")
async def encrypt(interaction: discord.Interaction, message: str, key: str):
    await interaction.response.defer()
    try:
        norm_key = _normalize_fernet_key(key)
        fernet = Fernet(norm_key)
        encrypted = fernet.encrypt(message.encode()).decode()
        # Simplificado: siempre mostramos solo el texto encriptado; la misma passphrase sirve para desencriptar.
        await interaction.followup.send(f"Mensaje encriptado:\n```\n{encrypted}\n```")
    except Exception as e:
        await interaction.followup.send(f"No pude encriptar el mensaje: {e}", ephemeral=True)


@bot.tree.command(name="decrypt", description="Desencripta un mensaje")
async def decrypt(interaction: discord.Interaction, message: str, key: str):
    await interaction.response.defer()
    try:
        norm_key = _normalize_fernet_key(key)
        fernet = Fernet(norm_key)
        decrypted = fernet.decrypt(message.encode()).decode()
        await interaction.followup.send(f"Mensaje desencriptado:\n```\n{decrypted}\n```")
    except Exception as e:
        await interaction.followup.send(f"No pude desencriptar el mensaje: {e}", ephemeral=True)

@bot.tree.command(name="hash", description="Genera un hash de un mensaje(por defecto Sha-256)")
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
            await interaction.followup.send(f"Algoritmo no soportado: {algorithm}", ephemeral=True)
            return

        hash_hex = hash_object.hexdigest()
        await interaction.followup.send(f"Hash ({algorithm}):\n```\n{hash_hex}\n```")
    except Exception as e:
        await interaction.followup.send(f"No pude generar el hash: {e}", ephemeral=True)

@bot.event
async def on_ready():
    # Sincroniza los slash commands con Discord al iniciar
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(f"No se pudieron sincronizar los comandos: {e}")
    user = getattr(bot, "user", None)
    if user:
        print(f"Conectado como {user} (ID: {user.id})")


if __name__ == "__main__":
    # Carga .env si python-dotenv está disponible
    try:
        import dotenv  # type: ignore
        # Buscar .env en cwd y junto al script, y soportar .ENV (Linux es case-sensitive)
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
        raise SystemExit("Falta la variable de entorno DISCORD_TOKEN.")
    bot.run(token)

