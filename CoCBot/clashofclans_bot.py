import os
import logging
import sqlite3
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Log-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("clashofclans_bot.log"),
        logging.StreamHandler()
    ]
)

# .env-Datei laden
load_dotenv()

# Discord-Bot-Konfiguration
BOT_TOKEN = os.getenv("DISCORD_TOKEN_CLASH")
COMMAND_PREFIX = "/"  # Standard-Präfix
INTENTS = discord.Intents.default()
INTENTS.messages = True
INTENTS.message_content = True

# SQLite-Datenbank
DATABASE_FILE = "clash_bot.db"


def initialize_database():
    """Initialisiert die SQLite-Datenbank."""
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT UNIQUE NOT NULL,
                channel_id INTEGER NOT NULL
            )
        """)
        connection.commit()
        connection.close()
        logging.info("Datenbank erfolgreich initialisiert.")
    except sqlite3.Error as e:
        logging.error(f"Fehler bei der Initialisierung der Datenbank: {e}")


class ClashBot(commands.Bot):
    """Erweiterter Bot für Clash of Clans."""

    def __init__(self, command_prefix, intents, database_file):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.database_file = database_file
        self.cogs_list = [
            "cogs.clanspiele",
            "cogs.clanwar",
            "cogs.clancapital",
            "cogs.verification",
            "cogs.general"
        ]

    async def setup_hook(self):
        """Setup-Hook für den Bot."""
        loaded_cogs = []
        failed_cogs = []

        # Cogs laden
        for cog in self.cogs_list:
            try:
                await self.load_extension(cog)
                loaded_cogs.append(cog)
            except Exception as e:
                failed_cogs.append((cog, str(e)))
                logging.error(f"Fehler beim Laden des Cogs {cog}: {e}")

        # Zusammenfassung der geladenen Cogs
        if loaded_cogs:
            logging.info(f"{len(loaded_cogs)} Cogs erfolgreich geladen: {', '.join(loaded_cogs)}")
        if failed_cogs:
            for cog, error in failed_cogs:
                logging.error(f"Cog {cog} konnte nicht geladen werden: {error}")

        # Command-Tree synchronisieren
        try:
            synced_commands = await self.tree.sync()
            logging.info(f"{len(synced_commands)} Befehle erfolgreich synchronisiert:")
            for command in synced_commands:
                logging.info(f" - {command.name} ({command.description})")
        except Exception as e:
            logging.error(f"Fehler beim Synchronisieren des Command-Trees: {e}")

    async def on_ready(self):
        """Event: Bot ist bereit."""
        logging.info(f"Eingeloggt als {self.user} (ID: {self.user.id})")
        logging.info("Bot ist bereit und läuft...")


async def main():
    """Startet den Bot."""
    logging.info("Bot wird gestartet...")
    initialize_database()

    bot = ClashBot(command_prefix=COMMAND_PREFIX, intents=INTENTS, database_file=DATABASE_FILE)

    if not BOT_TOKEN:
        logging.error("DISCORD_BOT_TOKEN ist nicht gesetzt.")
        exit(1)

    try:
        await bot.start(BOT_TOKEN)
    except Exception as e:
        logging.error(f"Fehler beim Starten des Bots: {e}")


if __name__ == "__main__":
    asyncio.run(main())
