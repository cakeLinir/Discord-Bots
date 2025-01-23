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
# Umgebungsvariablen laden
load_dotenv()


class ClashOfClansBot(commands.Bot):
    def __init__(self, token):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True  # Für App-Commands erforderlich

        super().__init__(command_prefix="/", intents=intents)
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
        """Setup für den Bot."""
        print("Clash of Clans Bot wird initialisiert...")
        # Verbinde zur Datenbank
        self.connect_to_database()

        # Cogs hinzufügen
        await self.load_cogs()
        synced = await self.tree.sync()
        print(f"Slash-Commands wurden synchronisiert: {len(synced)} Commands.")

    async def load_cogs(self):
        """Cogs laden."""
        for cog in ["cogs.verification",
                    "cogs.privacy",
                    "cogs.events",
                    "cogs.membercheck",
                    "cogs.general",
                    "cogs.embed"
                    ]:
            try:
                await self.load_extension(cog)
                print(f"Cog {cog} erfolgreich geladen.")
            except Exception as e:
                print(f"Fehler beim Laden von {cog}: {e}")

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
    load_dotenv()  # Umgebungsvariablen laden
    token = os.getenv("DISCORD_TOKEN_CLASH")
    if not token:
        raise ValueError("Kein Token für den Clash of Clans Bot gefunden!")
    bot = ClashOfClansBot(token)
    bot.start_bot()
