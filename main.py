import discord
from discord.ext import commands
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

API_URL = "https://linkvertise-api.onrender.com"  # <- zamień na swój link po deployu

@bot.command()
async def short(ctx, url):
    try:
        requests.post(f"{API_URL}/api/new-link", json={"url": url})
        await ctx.send("🔧 Tworzenie linka...")

        for _ in range(10):
            time.sleep(3)
            r = requests.get(f"{API_URL}/api/result")
            data = r.json()
            if data.get("link"):
                await ctx.send(f"✅ Gotowy link: {data['link']}")
                return

        await ctx.send("❌ Nie udało się wygenerować linka.")
    except Exception as e:
        await ctx.send(f"⚠️ Błąd: {str(e)}")

bot.run(os.getenv("DISCORD_TOKEN"))
