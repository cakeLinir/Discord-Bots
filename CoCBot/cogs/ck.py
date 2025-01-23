import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)


class ClanKriege(commands.Cog):
    """Clan-Kriege-Management."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ck_status", description="Zeigt den aktuellen Clan-Krieg-Status.")
    async def ck_status(self, interaction: discord.Interaction):
        """Holt den aktuellen Status des Clan-Krieges."""
        try:
            # Fiktiver Abruf der CK-Daten (Anpassung nötig)
            ck_data = {"state": "warEnded", "clan_stars": 45, "opponent_stars": 30}

            embed = discord.Embed(
                title="Clan-Kriege Status",
                description="Aktueller Stand des Clan-Krieges.",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Status", value=ck_data["state"], inline=False)
            embed.add_field(name="Unsere Sterne", value=ck_data["clan_stars"], inline=True)
            embed.add_field(name="Gegner-Sterne", value=ck_data["opponent_stars"], inline=True)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des CK-Status: {e}")
            await interaction.response.send_message("Fehler beim Abrufen des CK-Status.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ClanKriege(bot))
