import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import certifi
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cwl_check.start()
        self.clanspiele_check.start()
        self.ck_check.start()

    def cog_unload(self):
        self.cwl_check.cancel()
        self.clanspiele_check.cancel()
        self.ck_check.cancel()

    @tasks.loop(hours=1)  # Alle 1 Stunde
    async def cwl_check(self):
        """Prüft CWL-Status und postet Updates."""
        try:
            data = self.get_event_data("CWL")  # Fiktive Funktion
            if data:
                channel = self.get_event_channel("CWL")
                if channel:
                    embed = self.build_event_embed("CWL", data)
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Fehler beim CWL-Check: {e}")

    @tasks.loop(hours=1)
    async def clanspiele_check(self):
        """Prüft Clan-Spiele-Status und postet Updates."""
        try:
            data = self.get_event_data("Clanspiele")  # Fiktive Funktion
            if data:
                channel = self.get_event_channel("Clanspiele")
                if channel:
                    embed = self.build_event_embed("Clanspiele", data)
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Fehler beim Clan-Spiele-Check: {e}")

    @tasks.loop(hours=1)
    async def ck_check(self):
        """Prüft CK-Status und postet Updates."""
        try:
            data = self.get_event_data("CK")  # Fiktive Funktion
            if data:
                channel = self.get_event_channel("CK")
                if channel:
                    embed = self.build_event_embed("CK", data)
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Fehler beim CK-Check: {e}")

    @cwl_check.before_loop
    @clanspiele_check.before_loop
    @ck_check.before_loop
    async def before_checks(self):
        """Warte, bis der Bot bereit ist."""
        await self.bot.wait_until_ready()

    def get_event_data(self, event_type: str) -> dict:
        """Holt die relevanten Daten von der API für das angegebene Event."""
        try:
            url = f"https://api.clashofclans.com/v1/events/{event_type.lower()}"  # Beispiel-Endpoint
            headers = {"Authorization": f"Bearer {os.getenv('COC_API_TOKEN')}"}
            response = requests.get(url, headers=headers, verify=certifi.where())
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen der Daten für {event_type}: {response.text}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Event-Daten für {event_type}: {e}")
            return None

    def get_event_channel(self, event_type: str) -> discord.TextChannel:
        """Holt den Discord-Channel für das Event aus der Konfiguration."""
        try:
            channel_id = os.getenv(f"{event_type.upper()}_CHANNEL_ID")
            return self.bot.get_channel(int(channel_id)) if channel_id else None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Channels für {event_type}: {e}")
            return None

    def build_event_embed(self, event_type: str, data: dict) -> discord.Embed:
        """Erstellt ein Embed für das Event."""
        embed = discord.Embed(
            title=f"{event_type} Update",
            description=f"Details zum {event_type}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow(),
        )
        # Beispiel-Daten aus der API einfügen
        embed.add_field(name="Start", value=data.get("start_time", "N/A"), inline=True)
        embed.add_field(name="Ende", value=data.get("end_time", "N/A"), inline=True)
        embed.add_field(name="Details", value=data.get("details", "Keine weiteren Details verfügbar"), inline=False)
        embed.set_footer(text="Clash of Clans Events", icon_url="https://example.com/icon.png")
        return embed

    @app_commands.command(name="set_event_channel", description="Setzt den Channel für ein Event.")
    @commands.has_permissions(administrator=True)
    async def set_event_channel(self, interaction: discord.Interaction, event_type: str, channel: discord.TextChannel):
        """Setzt den Channel für ein Event."""
        try:
            env_var = f"{event_type.upper()}_CHANNEL_ID"
            os.environ[env_var] = str(channel.id)
            await interaction.response.send_message(f"Channel für {event_type} auf {channel.mention} gesetzt.",
                                                    ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Setzen des Channels für {event_type}: {e}")
            await interaction.response.send_message("Fehler beim Setzen des Channels.", ephemeral=True)

    @app_commands.command(name="announce_event", description="Postet ein Event manuell.")
    @commands.has_permissions(administrator=True)
    async def announce_event(self, interaction: discord.Interaction, event_type: str):
        """Postet ein Event manuell."""
        try:
            data = self.get_event_data(event_type)
            if data:
                channel = self.get_event_channel(event_type)
                if channel:
                    embed = self.build_event_embed(event_type, data)
                    await channel.send(embed=embed)
                    await interaction.response.send_message(f"Event **{event_type}** wurde erfolgreich angekündigt.",
                                                            ephemeral=True)
                else:
                    await interaction.response.send_message(f"Kein Channel für Event {event_type} gesetzt.",
                                                            ephemeral=True)
            else:
                await interaction.response.send_message(f"Keine Daten für Event {event_type} gefunden.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Ankündigen des Events {event_type}: {e}")
            await interaction.response.send_message("Fehler beim Ankündigen des Events.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Events(bot))
