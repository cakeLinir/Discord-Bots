import discord
from discord import app_commands
from discord.ext import commands


class General(commands.Cog):
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
        embed.add_field(name="Entwickler", value="<@333006296611684352>", inline=False)
        embed.add_field(name="Status", value="Online", inline=False)
        embed.set_footer(text="Clash of Clans Bot - Immer für dich da!")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
