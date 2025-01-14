import os
import asyncio
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Lade die Umgebungsvariablen
load_dotenv("../.env")


def get_bot_token(bot_name):
    """Gibt den Bot-Token basierend auf dem Namen zurück."""
    token_key = f"DISCORD_TOKEN_{bot_name.upper()}"
    token = os.getenv(token_key)
    if not token:
        raise ValueError(f"Kein Token für den Bot '{bot_name}' gefunden. Überprüfe die .env-Datei.")
    return token


# Bot-Name und Token abrufen
BOT_NAME = "support"
DISCORD_TOKEN = get_bot_token(BOT_NAME)

# Bot-Konfiguration laden
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"❌ Konfigurationsdatei nicht gefunden: {CONFIG_PATH}")

with open(CONFIG_PATH, "r") as config_file:
    config = json.load(config_file)

APPLICATION_ID = config.get("application_id")
if not APPLICATION_ID:
    raise ValueError("❌ 'application_id' fehlt in der Konfigurationsdatei.")

# Bot-Initialisierung
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents, application_id=int(config["application_id"]))


# Event: Bot ist bereit
@bot.event
async def on_ready():
    print("Slash-Commands werden synchronisiert...")
    await bot.tree.sync()
    print("Slash-Commands synchronisiert!")
    print(f"✅ Bot ist bereit! Eingeloggt als {bot.user} (ID: {bot.user.id})")
    print(f"✅ Verbundene Server: {[guild.name for guild in bot.guilds]}")
    print(f"✅ Intents aktiviert: {bot.intents}")


# Lade Cogs
async def load_cogs():
    # Pfad eine Ebene höher suchen
    cogs_directory = os.path.join(os.path.dirname(__file__), "cogs")
    print(f"[DEBUG] Cogs-Verzeichnis: {cogs_directory}")

    if not os.path.exists(cogs_directory):
        print("❌ Der Ordner 'cogs' existiert nicht.")
        return

    for filename in os.listdir(cogs_directory):
        if filename.endswith(".py") and filename != "__init__.py":
            cog_name = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(cog_name)
                print(f"✅ Cog '{cog_name}' erfolgreich geladen.")
            except Exception as e:
                print(f"❌ Fehler beim Laden des Cogs '{cog_name}': {e}")

    




# Main-Funktion
async def main():
    async with bot:
        print("✅ Starte Bot...")
        await load_cogs()
        await bot.start(DISCORD_TOKEN)


# Bot ausführen
if __name__ == "__main__":
    asyncio.run(main())
