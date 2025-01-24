import discord
from discord.ext import commands
from dotenv import load_dotenv
import pymysql
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClashOfClansBot(commands.Bot):
    def __init__(self, token):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True  # Für App-Commands erforderlich
        super().__init__(command_prefix="/", intents=intents)

        self.token = token
        self.db_connection = None  # Datenbankverbindung

    def connect_to_database(self):
        """Verbindet den Bot mit der Datenbank."""
        try:
            self.db_connection = pymysql.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("COC_DB_NAME"),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("Erfolgreich mit der Datenbank verbunden.")
        except pymysql.MySQLError as e:
            logger.error(f"Fehler bei der Verbindung zur Datenbank: {e}")
            raise

    async def setup_hook(self):
        """Lädt alle Cogs."""
        self.connect_to_database()  # Datenbankverbindung herstellen
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    logger.info(f"Cog {cog_name} erfolgreich geladen.")
                except Exception as e:
                    logger.error(f"Fehler beim Laden von {cog_name}: {e}")

    async def close(self):
        """Schließt den Bot und die Datenbankverbindung."""
        if self.db_connection:
            self.db_connection.close()
            logger.info("Datenbankverbindung geschlossen.")
        await super().close()

    def start_bot(self):
        """Startet den Bot."""
        self.run(self.token)


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN_CLASH")
    if not token:
        raise ValueError("Discord-Token nicht gefunden. Bitte .env-Datei überprüfen.")
    bot = ClashOfClansBot(token)
    bot.start_bot()
