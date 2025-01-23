import discord
from discord.ext import commands
from discord import app_commands
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Events(commands.Cog):
    """Grundsatz für Events-Management."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_event_channel", description="Setzt den Discord-Kanal für ein Event.")
    @app_commands.choices(
        event_type=[
            app_commands.Choice(name="Clan-War-League (CWL)", value="cwl"),
            app_commands.Choice(name="Clan-Kriege (CK)", value="ck"),
            app_commands.Choice(name="Clan-Spiele", value="clanspiele"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_event_channel(self, interaction: discord.Interaction, event_type: app_commands.Choice[str],
                                channel: discord.TextChannel):
        """Setzt den Kanal für ein spezifisches Event."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                INSERT INTO event_channels (event_type, channel_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE channel_id = VALUES(channel_id)
            """, (event_type.value, channel.id))
            self.bot.db_connection.commit()
            cursor.close()

            await interaction.response.send_message(
                f"Der Kanal für **{event_type.name}** wurde erfolgreich auf {channel.mention} gesetzt.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Setzen des Event-Kanals: {e}")
            await interaction.response.send_message("Fehler beim Setzen des Kanals.", ephemeral=True)

    def get_event_channel(self, event_type: str) -> discord.TextChannel:
        """Holt den Discord-Kanal für das Event aus der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                SELECT channel_id FROM event_channels WHERE event_type = %s
            """, (event_type,))
            result = cursor.fetchone()
            cursor.close()
            if result:
                return self.bot.get_channel(result[0])
            return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Kanals für {event_type}: {e}")
            return None


async def setup(bot):
    await bot.add_cog(Events(bot))
