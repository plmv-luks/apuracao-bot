import asyncio
import os

import discord
import yaml
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

with open("config.yaml", encoding="utf-8") as arquivo:
    CONFIG = yaml.safe_load(arquivo)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
bot.config = CONFIG


@bot.event
async def on_ready():
    print(f"Logado como {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} comando(s) sincronizado(s).")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")


async def carregar_cogs():
    for arquivo in os.listdir("./cogs"):
        if arquivo.endswith(".py") and not arquivo.startswith("_"):
            extensao = f"cogs.{arquivo[:-3]}"
            try:
                await bot.load_extension(extensao)
                print(f"Cog carregada: {extensao}")
            except Exception as e:
                print(f"Erro ao carregar {extensao}: {e}")


async def main():
    async with bot:
        await carregar_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
