import os
import discord
from discord.ext import commands
from discord import app_commands
import psutil

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)



@bot.tree.command(name="Ejemplo", description="Te saluda")
async def ejemplo(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hola, {interaction.user.mention}!")


@bot.tree.command(name="stats",description="Muestra estadísticas")
async def stats(interaction: discord.Interaction):
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    tmp = psutil.disk_usage('/tmp')
    uptime = psutil.boot_time()
    stats_msg = (
        f"**Estadísticas de la Raspberry Pi:**\n"
        f"CPU: {cpu}%\n"
        f"RAM: {mem.percent}% ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)\n"
        f"Disco: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)\n"
        f"TMP: {tmp.percent}% ({tmp.used // (1024**3)}GB / {tmp.total // (1024**3)}GB)\n"
        f"Uptime: {uptime} segundos"
    )
    await interaction.response.send_message(stats_msg)

@bot.tree.command(name="reboot", description="Reinicia la Raspberry Pi")
async def reboot(interaction: discord.Interaction):
    os.system("sudo reboot")
    await interaction.response.send_message("Reiniciando la Raspberry Pi...")

@bot.tree.command(name="shutdown", description="Apaga la Raspberry Pi")
async def shutdown(interaction: discord.Interaction):
    os.system("sudo shutdown now")
    await interaction.response.send_message("Apagando la Raspberry Pi...")

@bot.tree.command(name="update", description="Actualiza el sistema")
async def update(interaction: discord.Interaction):
    os.system("sudo apt update && sudo apt upgrade -y")
    await interaction.response.send_message("Actualizando el sistema...")

@bot.tree.command(name="vpnstatus", description="Muestra el estado de la VPN")
async def vpnstatus(interaction: discord.Interaction):
    vpn_status = os.popen("sudo wg show").read()
    await interaction.response.send_message(f"Estado de la VPN:\n{vpn_status}")

@bot.tree.command(name="vpnadduser", description="Agrega un nuevo usuario a la VPN")
async def vpnadduser(interaction: discord.Interaction):
   await interaction.response.send_message(
        
    )
   
@bot.tree.command(name="vpnremoveuser", description="Elimina un usuario de la VPN")
async def vpnremoveuser(interaction: discord.Interaction):
    await interaction.response.send_message()

@bot.tree.command(name="vpnlistusers", description="Lista los usuarios de la VPN")
async def vpnlistusers(interaction: discord.Interaction):
    await interaction.response.send_message()

@bot.tree.command(name="netdevices", description="Lista los dispositivos conectados a la red")
async def netdevices(interaction: discord.Interaction):
    net_devices = os.popen("ip neigh").read()
    await interaction.response.send_message(f"Dispositivos conectados a la red:\n{net_devices}")
