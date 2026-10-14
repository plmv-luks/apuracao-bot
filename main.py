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
    await bot.tree.sync()
    print(f"online como {bot.user}")


async def main():
    async with bot:
        await bot.load_extension("cogs.eleicao")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
