import os
import sys
import json
import time
import requests
import discord
import asyncio
from discord.ext import commands, tasks
from discord import Embed, app_commands
from discord.ui import Button, View
from dotenv import load_dotenv

# Pfad zur Konfigurationsdatei
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as config_file:
    CONFIG = json.load(config_file)

# Lade Umgebungsvariablen
load_dotenv("../.env")

def get_bot_token(bot_name):
    """Holt den Bot-Token basierend auf dem Namen."""
    token_key = f"DISCORD_TOKEN_{bot_name.upper()}"
    token = os.getenv(token_key)
    if not token:
        raise ValueError(f"Kein Token für den Bot '{bot_name}' gefunden. Überprüfe die .env-Datei.")
    return token

if len(sys.argv) > 1:
    BOT_NAME = sys.argv[1].lower()
else:
    BOT_NAME = "twitch"

DISCORD_TOKEN = get_bot_token(BOT_NAME)
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET or not DISCORD_TOKEN:
    raise ValueError("Eine oder mehrere Umgebungsvariablen fehlen. Bitte überprüfe die .env-Datei.")

TWITCH_NOTIFICATIONS_CHANNEL_ID = int(CONFIG.get("twitch_notifications_channel_id"))
TWITCH_CHANNEL_NAMES = CONFIG.get("twitch_channel_names", [])
if not TWITCH_CHANNEL_NAMES:
    print("Die Liste der Twitch-Streamer ist leer. Bitte füge Streamer in die config.json hinzu.")

# Discord Bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Twitch API-Variablen
twitch_api_token = None
STATUS_FILE = "live_status.json"

class TwitchButtonView(View):
    """View mit einem Button zum Twitch-Kanal."""
    def __init__(self, streamer_name, streamer_url):
        super().__init__()
        self.add_item(Button(label=streamer_name, url=streamer_url, style=discord.ButtonStyle.link))

def load_live_status():
    """Lädt den Live-Status aus einer Datei."""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as file:
            return json.load(file)
    return {streamer_name: False for streamer_name in TWITCH_CHANNEL_NAMES}

def save_live_status(status):
    """Speichert den Live-Status in einer Datei."""
    with open(STATUS_FILE, "w") as file:
        json.dump(status, file)

    print(f"Live-Status wurde aktualisiert: {status}")

last_live_status = load_live_status()

def save_streamer_list():
    """Speichert die aktuelle Streamer-Liste in der Konfiguration."""
    global TWITCH_CHANNEL_NAMES
    CONFIG["twitch_channel_names"] = TWITCH_CHANNEL_NAMES
    with open(CONFIG_PATH, "w") as config_file:
        json.dump(CONFIG, config_file, indent=4)

    print(f"Die Streamer-Liste wurde aktualisiert: {TWITCH_CHANNEL_NAMES}")

def get_twitch_api_token():
    """Holt das Twitch API Token."""
    global twitch_api_token
    url = "https://id.twitch.tv/oauth2/token"
    params = {"client_id": TWITCH_CLIENT_ID, "client_secret": TWITCH_CLIENT_SECRET, "grant_type": "client_credentials"}
    response = requests.post(url, params=params)
    response.raise_for_status()
    twitch_api_token = response.json()["access_token"]

def fetch_profile_image(user_name):
    """Holt das Profilbild eines Twitch-Nutzers."""
    url = f"https://api.twitch.tv/helix/users?login={user_name.strip()}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {twitch_api_token}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()["data"]
    if len(data) > 0:
        return data[0]["profile_image_url"]
    return None

def is_channel_live(streamer_name):
    """Prüft, ob der Twitch-Kanal live ist."""
    try:
        if not twitch_api_token:
            get_twitch_api_token()
        url = f"https://api.twitch.tv/helix/streams?user_login={streamer_name.strip()}"
        headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {twitch_api_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()["data"]
        return len(data) > 0, data[0] if data else None
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen des Live-Status für {streamer_name}: {e}")
        return False, None

@tasks.loop(minutes=1)
async def check_twitch_streams():
    """Überprüft Twitch-Streams und sendet Benachrichtigungen."""
    global last_live_status

    channel = bot.get_channel(TWITCH_NOTIFICATIONS_CHANNEL_ID)
    if not channel:
        print(f"Channel mit der ID {TWITCH_NOTIFICATIONS_CHANNEL_ID} nicht gefunden.")
        return

    for streamer_name in TWITCH_CHANNEL_NAMES:
        is_live, stream_data = is_channel_live(streamer_name)
        if is_live and not last_live_status.get(streamer_name, False):
            thumbnail_url = stream_data["thumbnail_url"].format(width=1280, height=720)
            profile_image_url = fetch_profile_image(streamer_name)

            # Embed erstellen
            embed = Embed(
                title=f"🔴 {stream_data['user_name']} ist jetzt live!",
                description=f"**{stream_data['title']}**\n[Jetzt zuschauen!](https://www.twitch.tv/{streamer_name})",
                color=0x9146FF,
            )
            if profile_image_url:
                embed.set_thumbnail(url=profile_image_url)
            embed.add_field(name="🎮 Spiel", value=stream_data.get("game_name", "Nicht angegeben"), inline=True)
            embed.add_field(name="👥 Zuschauer", value=stream_data["viewer_count"], inline=True)
            embed.set_image(url=thumbnail_url)
            embed.set_footer(
                text="Twitch",
                icon_url="https://static.twitchcdn.net/assets/favicon-32-d6025c14e900565d6177.png"
            )

            # Nachricht senden mit Button
            stream_url = f"https://www.twitch.tv/{streamer_name}"
            view = TwitchButtonView(stream_data["user_name"],
                                    stream_url)  # Verwende den Namen des Streamers als Button-Label
            await channel.send(embed=embed, view=view)

            last_live_status[streamer_name] = True
            save_live_status(last_live_status)
        elif not is_live and last_live_status.get(streamer_name, False):
            last_live_status[streamer_name] = False
            save_live_status(last_live_status)
        time.sleep(0.5)

@bot.tree.command(name="streamer", description="Streamer hinzufügen oder entfernen.")
@app_commands.describe(
    action="Aktion: add (Hinzufügen) oder remove (Entfernen)",
    name="Name des Streamers"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Hinzufügen", value="add"),
    app_commands.Choice(name="Entfernen", value="remove"),
])
async def streamer(interaction: discord.Interaction, action: str, name: str):
    """Verwaltet die Liste der Twitch-Streamer."""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Nur Administratoren können diesen Command verwenden.", ephemeral=True)
        return

    global TWITCH_CHANNEL_NAMES

    name = name.strip().lower()
    if action == "add":
        if name in TWITCH_CHANNEL_NAMES:
            await interaction.response.send_message(f"Streamer **{name}** ist bereits in der Liste.", ephemeral=True)
            return

        TWITCH_CHANNEL_NAMES.append(name)
        save_streamer_list()
        await interaction.response.send_message(f"Streamer **{name}** wurde erfolgreich hinzugefügt.", ephemeral=True)

    elif action == "remove":
        if name not in TWITCH_CHANNEL_NAMES:
            await interaction.response.send_message(f"Streamer **{name}** ist nicht in der Liste.", ephemeral=True)
            return

        TWITCH_CHANNEL_NAMES.remove(name)
        save_streamer_list()
        await interaction.response.send_message(f"Streamer **{name}** wurde erfolgreich entfernt.", ephemeral=True)

@bot.tree.command(name="streamer_list", description="Zeigt die Liste der aktuell überwachten Streamer an.")
async def streamer_list(interaction: discord.Interaction):
    """Zeigt die Liste der Twitch-Streamer."""
    if not TWITCH_CHANNEL_NAMES:
        await interaction.response.send_message(
            "Es werden derzeit keine Streamer überwacht.", ephemeral=True
        )
        return

    streamer_list = "\n".join(f"- {streamer}" for streamer in TWITCH_CHANNEL_NAMES)
    await interaction.response.send_message(
        f"**Aktuell überwachte Streamer:**\n{streamer_list}", ephemeral=True
    )

@bot.event
async def on_ready():
    """Wird aufgerufen, wenn der Bot bereit ist."""
    if not check_twitch_streams.is_running():
        print(f"Bot ist bereit! Eingeloggt als {bot.user}")
        check_twitch_streams.start()
    try:
        await bot.tree.sync()
        print("Slash-Commands synchronisiert.")
    except Exception as e:
        print(f"Fehler beim Synchronisieren der Slash-Commands: {e}")

async def main():
    """Startet den Bot mit allen Cogs."""
    async with bot:
        await bot.start(DISCORD_TOKEN)

# Starte die asynchrone Hauptfunktion
if __name__ == "__main__":
    asyncio.run(main())
