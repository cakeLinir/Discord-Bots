import discord
import pymysql
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Umgebungsvariablen laden
load_dotenv()


class ClashOfClansBot(commands.Bot):
    def __init__(self, token, command_prefix):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True  # Für App-Commands erforderlich
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.token = token
        self.db_connection = None  # Initialisiere die Datenbankverbindung

    def connect_to_database(self):
        """Verbindet sich mit der Datenbank."""
        try:
            self.db_connection = pymysql.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("COC_DB_NAME")
            )
            logger.info("Erfolgreich mit der Datenbank verbunden.")
        except pymysql.MySQLError as e:
            logger.error(f"Fehler bei der Verbindung zur Datenbank: {e}")
            raise

    async def setup_hook(self):
        """Initialisiert den Bot und synchronisiert Befehle."""
        self.connect_to_database()  # Stelle die Datenbankverbindung her
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = f"cogs.{filename[:-3]}"  # Entfernt die .py-Erweiterung
                try:
                    await self.load_extension(cog_name)
                    print(f"Cog {cog_name} erfolgreich geladen.")
                except Exception as e:
                    print(f"Fehler beim Laden von {cog_name}: {e}")

        # Synchronisiere App-Commands
        synced = await self.tree.sync()
        print(f"Synchronisierte {len(synced)} Befehle:")
        for command in synced:
            print(f" - {command.name}")

    async def close(self):
        """Schließt den Bot und die Datenbankverbindung."""
        if self.db_connection:
            self.db_connection.close()
            logger.info("Datenbankverbindung geschlossen.")
        await super().close()

    def start_bot(self):
        """Bot starten."""
        self.run(self.token)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN_CLASH")
    if not token:
        raise ValueError("Kein Token für den Clash of Clans Bot gefunden!")
    bot = ClashOfClansBot(token, command_prefix="/")
    bot.start_bot()
