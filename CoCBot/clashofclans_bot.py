import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os

from CoCBot.cogs.verification import Verification
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

    async def setup_hook(self):
        """Setup für den Bot."""
        logger.info("Clash of Clans Bot wird initialisiert...")
        await self.load_cogs()
        synced = await self.tree.sync()
        logger.info(f"Slash-Commands wurden synchronisiert: {len(synced)} Commands.")

    async def load_cogs(self):
        """Cogs laden."""
        cogs = ["cogs.verification", "cogs.privacy", "cogs.events", "cogs.general"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog {cog} erfolgreich geladen.")
            except Exception as e:
                logger.error(f"Fehler beim Laden von {cog}: {e}")

    async def on_ready(self):
        """Event: Bot ist bereit."""
        logger.info(f"{self.user} ist bereit und eingeloggt!")

    def start_bot(self):
        """Bot starten."""
        self.run(self.token)


class GeneralCommands(commands.Cog):
    """Allgemeine Commands für den Clash of Clans Bot."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Prüft, ob der Bot online ist.")
    async def ping(self, interaction: discord.Interaction):
        """Ein einfacher Ping-Befehl."""
        await interaction.response.send_message("Pong! Der Bot ist online.")

    @app_commands.command(name="info", description="Zeigt Informationen zum Clash of Clans Bot an.")
    async def info(self, interaction: discord.Interaction):
        """Zeigt allgemeine Informationen über den Bot."""
        embed = discord.Embed(
            title="Clash of Clans Bot",
            description="Ein Bot zur Verwaltung und Unterstützung von Clan-Mitgliedern.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Version", value="1.0", inline=False)
        embed.add_field(name="Entwickler", value="Dein Team", inline=False)
        await interaction.response.send_message(embed=embed)


# Falls diese Datei direkt ausgeführt wird
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN_CLASH")
    if not token:
        raise ValueError("Kein Token für den Clash of Clans Bot gefunden!")
    bot = ClashOfClansBot(token)
    bot.start_bot()
