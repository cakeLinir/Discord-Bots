import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os

# Umgebungsvariablen laden
load_dotenv()

class SupportBot(commands.Bot):
    def __init__(self, token):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True  # Für Slash-Commands erforderlich
        intents.members = True  # Für Moderation und Benutzer-Management

        super().__init__(command_prefix="/", intents=intents)
        self.token = token

    async def setup_hook(self):
        """Setup für den Bot."""
        print("Support Bot wird initialisiert...")

        # Beispiel: Einen Cog hinzufügen
        await self.add_cog(GeneralSupportCommands(self))

    async def on_ready(self):
        """Event: Bot ist bereit."""
        print(f"{self.user} ist bereit und eingeloggt!")

    def start_bot(self):
        """Bot starten."""
        self.run(self.token)

class GeneralSupportCommands(commands.Cog):
    """Allgemeine Commands für den Support Bot."""
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Prüft, ob der Bot online ist.")
    async def ping(self, ctx):
        """Ein einfacher Ping-Befehl."""
        await ctx.respond("Pong! Der Support Bot ist online.")

    @app_commands.command(name="ticket", description="Erstellt ein neues Support-Ticket.")
    async def ticket(self, ctx):
        """Erstellt ein neues Support-Ticket."""
        # Placeholder für zukünftige Ticket-Logik
        embed = discord.Embed(
            title="Support-Ticket erstellt",
            description="Dein Support-Ticket wurde erstellt und ein Moderator wird sich bald darum kümmern.",
            color=discord.Color.green()
        )
        await ctx.respond(embed=embed)

# Falls diese Datei direkt ausgeführt wird
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN_SUPPORT")
    if not token:
        raise ValueError("Kein Token für den Support Bot gefunden!")
    bot = SupportBot(token)
    bot.start_bot()
