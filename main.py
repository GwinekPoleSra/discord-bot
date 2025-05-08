import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from flask import Flask
from threading import Thread
from linkvertise import LinkvertiseClient
import asyncio
import datetime

# ===== KONFIGURACJA ID KANAŁÓW =====
CODZIENNE_WYSLANIE_ID = 1353467599081439304  # wysyłka codziennych wiadomości
CODZIENNE_ZARZADZANIE_ID = 1359520357085872239  # zarządzanie codziennymi
LINKVERTISE_CHANNEL_ID = 1359536602283770076  # generowanie linków
EMBED_CREATOR_CHANNEL_ID = 1367485031219593296  # tworzenie embedów

# ===== FLASK KEEP ALIVE =====
app = Flask('')

@app.route('/')
def home():
    return "Bot działa! 👋"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===== BOT SETUP =====
TOKEN = os.getenv("TOKEN")
LINKVERTISE_ID = int(os.getenv("LINKVERTISE_ID"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

lv_client = LinkvertiseClient()

dni_polskie = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

def save_message_for_day(day, content):
    lines = []
    if os.path.exists('wiadomosci.txt'):
        with open('wiadomosci.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()

    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{day}:"):
            new_lines.append(f"{day}: {content}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{day}: {content}\n")

    with open('wiadomosci.txt', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def get_today_message():
    today_polish = dni_polskie.get(datetime.datetime.now().strftime("%A"))
    if os.path.exists('wiadomosci.txt'):
        with open('wiadomosci.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith(f"{today_polish}:"):
                    return line[len(today_polish)+2:].strip()
    return None

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}")
    send_daily_message.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id == LINKVERTISE_CHANNEL_ID:
        if message.content.startswith("http://") or message.content.startswith("https://"):
            try:
                monetized = lv_client.linkvertise(LINKVERTISE_ID, message.content)
                await message.channel.send(f"Oto Twój link z Linkvertise: {monetized}")
            except Exception as e:
                await message.channel.send(f"Błąd: {e}")

    elif message.channel.id == EMBED_CREATOR_CHANNEL_ID and message.content.lower() == "dodaj":
        await handle_dodaj(message)

    await bot.process_commands(message)

@tasks.loop(minutes=1)
async def send_daily_message():
    now = datetime.datetime.now() + datetime.timedelta(hours=2)
    if now.hour == 12 and now.minute == 0:
        channel = bot.get_channel(CODZIENNE_WYSLANIE_ID)
        if channel:
            message = get_today_message()
            if message:
                await channel.send(f"**CODZIENNY DYSK 👇👇**\n{message}")
            else:
                await channel.send("Brak zaplanowanej wiadomości na dziś.")

@bot.command()
async def poka(ctx):
    if ctx.channel.id != CODZIENNE_ZARZADZANIE_ID:
        return
    if os.path.exists('wiadomosci.txt'):
        with open('wiadomosci.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        await ctx.send(f"```\n{content}```" if content.strip() else "Plik jest pusty.")
    else:
        await ctx.send("Plik nie istnieje.")

@bot.command()
async def clear(ctx):
    if ctx.channel.id != CODZIENNE_ZARZADZANIE_ID:
        return
    with open('wiadomosci.txt', 'w', encoding='utf-8') as f:
        f.write('')
    await ctx.send("✅ Plik wyczyszczony.")

@bot.command()
async def dzis(ctx):
    message = get_today_message()
    await ctx.send(f"**CODZIENNY DYSK 👇👇**\n{message}" if message else "Brak wiadomości na dziś.")

dni_skroty = {
    "pon": "Poniedziałek", "wto": "Wtorek", "sro": "Środa",
    "czw": "Czwartek", "pia": "Piątek", "sob": "Sobota", "nie": "Niedziela"
}

for skrot, dzien in dni_skroty.items():
    @bot.command(name=skrot)
    async def set_day_msg(ctx, *, message, dzien=dzien):
        if ctx.channel.id != CODZIENNE_ZARZADZANIE_ID:
            return
        save_message_for_day(dzien, message)
        await ctx.send(f"✅ Zapisano wiadomość na **{dzien.lower()}**!")

# === Embedy ===
async def handle_dodaj(message):
    ctx = await bot.get_context(message)
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    await message.delete()

    async def ask(prompt):
        q = await ctx.send(prompt)
        m = await bot.wait_for('message', timeout=300, check=check)
        if m.content.lower() == "koniec":
            await ctx.send("❌ Proces anulowany.", delete_after=5)
            await q.delete(); await m.delete()
            return None
        await q.delete(); await m.delete()
        return m.content

    tytul = await ask("📝 Podaj tytuł:")
    if not tytul: return
    link = await ask("🔗 Podaj link:")
    if not link: return
    zdjecie = await ask("🖼️ Podaj link do zdjęcia/gifa:")
    if not zdjecie: return

    poradnik_channel_id = 1323745795878424628
    poradnik_channel = ctx.guild.get_channel(poradnik_channel_id)
    embed = discord.Embed(title=tytul, description=f"[Kliknij tutaj]({link})\n\nJak to otworzyć ➔ {poradnik_channel.mention}", color=discord.Color.purple())
    embed.set_image(url=zdjecie)

    class ConfirmView(View):
        def __init__(self): super().__init__(timeout=60); self.value = None
        @discord.ui.button(label="TAK", style=discord.ButtonStyle.green)
        async def confirm(self, interaction, button): self.value = True; await interaction.response.defer(); self.stop()
        @discord.ui.button(label="NIE", style=discord.ButtonStyle.red)
        async def cancel(self, interaction, button): self.value = False; await interaction.response.defer(); self.stop()

    view = ConfirmView()
    preview = await ctx.send("✅ Podgląd embeda. Kontynuować?", embed=embed, view=view)
    await view.wait(); await preview.delete()

    if not view.value:
        await ctx.send("❌ Proces anulowany.", delete_after=5)
        return

    kanal = None
    while not kanal:
        nazwa = await ask("📢 Podaj fragment nazwy kanału:")
        if not nazwa: return
        pasujace = [k for k in ctx.guild.text_channels if nazwa.lower() in k.name.lower()]
        if not pasujace:
            await ctx.send("❌ Nie znaleziono kanału.", delete_after=5)
            continue
        if len(pasujace) == 1:
            kanal = pasujace[0]
        else:
            lista = "\n".join(f"{i+1}. {k.mention}" for i, k in enumerate(pasujace))
            msg = await ctx.send(f"🔢 Wybierz numer:\n{lista}")
            while True:
                nr_msg = await bot.wait_for('message', timeout=300, check=check)
                if nr_msg.content.lower() == "koniec":
                    await msg.delete(); await nr_msg.delete()
                    return
                if nr_msg.content.isdigit() and 1 <= int(nr_msg.content) <= len(pasujace):
                    kanal = pasujace[int(nr_msg.content)-1]
                    await nr_msg.delete(); break
                await ctx.send("❌ Zły numer.", delete_after=5); await nr_msg.delete()
            await msg.delete()

    await kanal.send(embed=embed)
    await ctx.channel.send(embed=embed)
    await ctx.send(f"✅ Embed wysłany na {kanal.mention} oraz tutaj!", delete_after=5)

# === URUCHOMIENIE ===
keep_alive()
bot.run(TOKEN)
