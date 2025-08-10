import os
import random
import string
from urllib import response
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
import psutil
import asyncio
import io
import subprocess
import datetime
import tempfile
from pathlib import Path
import base64
import json
import urllib.parse
from typing import Optional
import html
import pytz
import time
import platform

import urllib.request

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="help", description="Muestra la lista de comandos")
async def help(interaction: discord.Interaction):
    list=(
        "Comandos disponibles:\n"
        "- /help: Muestra la lista de comandos\n"
        "- /Ejemplo: Te saluda"
        ""
    )
    await interaction.response.send_message(list)

@bot.tree.command(name="ejemplo", description="Te saluda")
async def ejemplo(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hola, {interaction.user.mention}!")


@bot.tree.command(name="stats",description="Muestra estadísticas")
async def stats(interaction: discord.Interaction):
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    tmp = psutil.disk_usage('/tmp')
    # uptime en segundos desde el arranque
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
        f"**Estadísticas de la Raspberry Pi:**\n"
        f"CPU: {cpu}%\n"
        f"RAM: {mem.percent}% ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)\n"
        f"Disco: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)\n"
        f"TMP: {tmp.percent}% ({tmp.used // (1024**3)}GB / {tmp.total // (1024**3)}GB)\n"
        f"Uptime (DD:HH:MM:SS): {uptime_str}"
    )
    await interaction.response.send_message(stats_msg)

@bot.tree.command(name="reboot", description="Reinicia la Raspberry Pi")
async def reboot(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Reiniciando la Raspberry Pi...", ephemeral=True)
    # Run reboot in background to avoid blocking
    asyncio.create_task(asyncio.to_thread(os.system, "sudo reboot"))

@bot.tree.command(name="shutdown", description="Apaga la Raspberry Pi")
async def shutdown(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Apagando la Raspberry Pi...", ephemeral=True)
    asyncio.create_task(asyncio.to_thread(os.system, "sudo shutdown now"))

@bot.tree.command(name="update", description="Actualiza el sistema")
async def update(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Actualizando el sistema...", ephemeral=True)
    
    async def _run_update():
        code = await asyncio.to_thread(os.system, "sudo apt update && sudo apt upgrade -y")
        try:
            await interaction.followup.send(f"Actualización finalizada (código {code}).", ephemeral=True)
        except Exception:
            pass
    
    asyncio.create_task(_run_update())

@bot.tree.command(name="vpnstatus", description="Muestra el estado de la VPN")
async def vpnstatus(interaction: discord.Interaction):
    await interaction.response.defer()
    vpn_status = await asyncio.to_thread(lambda: os.popen("sudo wg show").read())
    await interaction.followup.send(f"Estado de la VPN:\n{vpn_status}")

@bot.tree.command(name="netdevices", description="Lista los dispositivos conectados a la red")
async def netdevices(interaction: discord.Interaction):
    await interaction.response.defer()
    net_devices = await asyncio.to_thread(lambda: os.popen("ip neigh").read())
    await interaction.followup.send(f"Dispositivos conectados a la red:\n{net_devices}")



@bot.tree.command(name="ping", description="Realiza un ping a una dirección IP")
async def ping(interaction: discord.Interaction, ip_address: str):
    await interaction.response.defer()
    # Use appropriate flag for Windows (-n) vs Linux (-c)
    flag = "-n" if platform.system().lower().startswith("win") else "-c"
    result = await asyncio.to_thread(lambda: os.popen(f"ping {flag} 4 {ip_address}").read())
    await interaction.followup.send(f"Resultado del ping a {ip_address}:\n{result}")

@bot.tree.command(name="shorten", description="Acorta una url")
async def shorten(interaction: discord.Interaction, url:str):
    await interaction.response.defer()
    result = await asyncio.to_thread(lambda: os.popen(f'curl -s "https://is.gd/create.php?format=simple&url={url}"').read())
    await interaction.followup.send(f"URL acortada:\n{result}")

@bot.tree.command(name="screenshotweb", description="Toma una captura de pantalla de una página web")
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
        file = discord.File(fp=io.BytesIO(image_bytes), filename="screenshot.png")
        await interaction.followup.send(content=f"Captura de pantalla de {url}:", file=file)
    except Exception as e:
        await interaction.followup.send(f"No se pudo obtener la captura: {e}")


@bot.tree.command(name="qr", description="Genera un código QR a partir de una URL")
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
        await interaction.followup.send(content=f"Código QR de {url}:", file=file)
    except Exception as e:
        await interaction.followup.send(f"No se pudo generar el código QR: {e}")


@bot.tree.command(name="passw", description="Genera una contraseña")
async def passw(interaction: discord.Interaction, chars: int):
    await interaction.response.defer()
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=chars))
    await interaction.followup.send(f"Aquí tienes tu contraseña: {password}")

@bot.tree.command(name="mergepdf", description="Junta varios PDF adjuntos en uno solo")
@app_commands.describe(
    file1="PDF 1 (obligatorio)",
    file2="PDF 2 (opcional)",
    file3="PDF 3 (opcional)",
    file4="PDF 4 (opcional)",
    file5="PDF 5 (opcional)",
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
        await interaction.followup.send("Adjunta al menos 2 PDFs.", ephemeral=True)
        return

    # Validación básica de tipo
    for a in attachments:
        name = (a.filename or "").lower()
        ctype = (a.content_type or "").lower()
        if not (name.endswith(".pdf") or "pdf" in ctype):
            await interaction.followup.send(f"'{a.filename}' no parece ser un PDF.", ephemeral=True)
            return

    try:
        from pypdf import PdfReader, PdfWriter  # type: ignore
    except Exception:
        await interaction.followup.send(
            "Falta la librería pypdf. Instálala con: pip install pypdf",
            ephemeral=True,
        )
        return

    # Descargar y fusionar
    writer = PdfWriter()
    try:
        for a in attachments:
            data = await a.read()
            reader = PdfReader(io.BytesIO(data))
            # Manejar PDFs encriptados sin contraseña
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    await interaction.followup.send(
                        f"El PDF '{a.filename}' está protegido y no se puede abrir.",
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
        await interaction.followup.send(f"No se pudieron combinar los PDFs: {e}", ephemeral=True)
        return

    merged_name = "merged.pdf"
    data = buf.getvalue()
    LIMIT = 24 * 1024 * 1024  # ~24 MiB seguro para adjuntar

    if len(data) <= LIMIT:
        await interaction.followup.send(
            content="Aquí tienes tu PDF combinado:",
            file=discord.File(fp=io.BytesIO(data), filename=merged_name),
        )
        return
    else:
        await interaction.followup.send(
            "El PDF combinado excede el límite para adjuntar",
            ephemeral=True,
        )

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
        os.system("sudo systemctl restart utilsbot.service")
    except Exception as e:
        await interaction.followup.send(f"No pude reiniciar el bot: {e}", ephemeral=True)
    await interaction.followup.send("Reiniciando el bot...", ephemeral=True)

@bot.tree.command(name="execute", description="Ejecuta un comando en la Raspberry Pi")
async def execute(interaction: discord.Interaction, command: str):
    await interaction.response.defer()
    try:
        output = await asyncio.to_thread(lambda: subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT))
        await interaction.followup.send(f"Salida del comando:\n```\n{output.decode()}\n```")
    except Exception as e:
        await interaction.followup.send(f"No pude ejecutar el comando: {e}", ephemeral=True)

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
    token = Secret""
    if not token:
        raise SystemExit("Falta la variable de entorno DISCORD_TOKEN.")
    bot.run(token)

