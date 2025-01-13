import discord
from discord.ext import commands
from discord import app_commands


class UserCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Überprüfe, ob der Bot bereit ist.")
    async def ping(self, interaction: discord.Interaction):
        """Ein einfacher Ping-Befehl."""
        await interaction.response.send_message("Pong! Der Bot ist bereit.", ephemeral=True)
        await self.bot.tree.sync()
        print(f"[DEBUG] Aktuelle Slash-Commands: {self.bot.tree.get_commands()}")


async def setup(bot):
    await bot.add_cog(UserCommands(bot))
