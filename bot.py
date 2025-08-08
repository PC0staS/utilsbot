import os
import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)



@bot.tree.command(name="Ejemplo", description="Te saluda")
async def ejemplo(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hola, {interaction.user.mention}!")


@bot.tree.command()