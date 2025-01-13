import discord
from discord.ext import commands
from discord import app_commands
from math import ceil


class UserCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.per_page = 5  # Anzahl der Befehle pro Seite

    @app_commands.command(name="ping", description="Überprüfe, ob der Bot bereit ist.")
    async def ping(self, interaction: discord.Interaction):
        """Ein einfacher Ping-Befehl."""
        await interaction.response.send_message("Pong! Der Bot ist bereit.", ephemeral=True)

    @app_commands.command(name="help", description="Zeigt eine Liste aller verfügbaren Befehle an.")
    async def help(self, interaction: discord.Interaction):
        """Zeigt eine interaktive Hilfeseite mit allen Befehlen an."""
        commands_dict = {
            "User Commands": [],
            "Moderation Commands": [],
            "Admin Commands": []
        }

        # Commands in Kategorien sortieren
        for cmd in self.bot.tree.get_commands():
            if cmd.name in ["ping"]:  # Beispiel für User Commands
                commands_dict["User Commands"].append(f"/{cmd.name}: {cmd.description}")
            elif cmd.name in ["ban", "unban", "kick", "mute", "unmute", "timeout"]:  # Moderations-Commands
                commands_dict["Moderation Commands"].append(f"/{cmd.name}: {cmd.description}")
            elif cmd.name in ["setup_tickets", "add_support_role", "remove_support_role"]:  # Admin-Commands
                commands_dict["Admin Commands"].append(f"/{cmd.name}: {cmd.description}")

        # Alle Commands für die Seitenanzeige vorbereiten
        categories = list(commands_dict.keys())
        total_pages = len(categories)

        async def generate_page(page):
            """Erstellt die Embed-Seite für die aktuelle Kategorie."""
            category = categories[page - 1]
            embed = discord.Embed(
                title=f"📖 Hilfe - {category}",
                description="\n".join(commands_dict[category]) if commands_dict[category] else "Keine Befehle in dieser Kategorie.",
                color=0x3498db
            )
            embed.set_image(
                url="https://via.placeholder.com/800x200.png?text=HILFE"  # Platzhalter-Hintergrund
            )
            embed.set_footer(text=f"Seite {page} von {total_pages}")
            return embed

        async def handle_reaction(embed_message, user):
            """Reagiert auf Benutzer-Interaktionen für die Seitenumschaltung."""
            def check(reaction, reactor):
                return (
                    reaction.message.id == embed_message.id
                    and reactor == user
                    and str(reaction.emoji) in ["⬅️", "➡️"]
                )

            page = 1
            while True:
                try:
                    reaction, reactor = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    if str(reaction.emoji) == "➡️" and page < total_pages:
                        page += 1
                    elif str(reaction.emoji) == "⬅️" and page > 1:
                        page -= 1
                    await embed_message.edit(embed=await generate_page(page))
                    await reaction.remove(reactor)
                except Exception:
                    break

        embed = await generate_page(1)
        message = await interaction.response.send_message(embed=embed, ephemeral=True)
        embed_message = await interaction.original_response()

        await embed_message.add_reaction("⬅️")
        await embed_message.add_reaction("➡️")
        await handle_reaction(embed_message, interaction.user)


async def setup(bot):
    await bot.add_cog(UserCommands(bot))
