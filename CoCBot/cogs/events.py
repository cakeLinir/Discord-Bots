import discord
from discord.ext import commands
from discord import app_commands
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Events(commands.Cog):
    """Globale Verwaltung der Events."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_event_channel", description="Setzt den Kanal für ein Event.")
    @app_commands.choices(event_type=[
        app_commands.Choice(name="Clanspiele", value="clanspiele"),
        app_commands.Choice(name="Clan-Krieg", value="ck"),
        app_commands.Choice(name="CWL", value="cwl")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def set_event_channel(self, interaction: discord.Interaction, event_type: app_commands.Choice[str],
                                channel: discord.TextChannel):
        """Setzt den Kanal für ein Event."""
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


async def setup(bot):
    await bot.add_cog(Events(bot))
