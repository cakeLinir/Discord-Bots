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

    @app_commands.command(name="help", description="Zeigt eine Liste aller verfügbaren Befehle.")
    async def help_command(self, interaction: discord.Interaction):
        """Zeigt eine interaktive Hilfeseite mit allen Befehlen an."""
        commands_dict = {
            "User Commands": ["/ping - Überprüfe, ob der Bot bereit ist.",
                              "➡️ Nächste Seite: Moderation Commands",],
            "Moderation Commands": [
                "/ban - Bannt einen Benutzer.",
                "/unban - Entbannt einen Benutzer.",
                "/kick - Kicked einen Benutzer.",
                "/mute - Muted einen Benutzer.",
                "/unmute - Entmutet einen Benutzer.",
                "➡️ Nächste Seite: Admin Commands",
                "⬅️ Vorherige Seite: User Commands",
            ],
            "Admin Commands": [
                "/setup_tickets - Richtet das Ticketsystem ein.",
                "/add_support_role - Fügt eine Supportrolle hinzu.",
                "/remove_support_role - Entfernt eine Supportrolle.",
                "⬅️ Vorherige Seite: Moderation Commands",
            ],
        }

        categories = list(commands_dict.keys())
        total_pages = len(categories)

        async def generate_page(page):
            """Erstellt die Embed-Seite für die aktuelle Kategorie."""
            category = categories[page - 1]
            previous_category = categories[page - 2] if page > 1 else "N/A"
            next_category = categories[page] if page < total_pages else "N/A"

            embed = discord.Embed(
                title=f"📖 Hilfe - {category}",
                description="\n".join(commands_dict[category]) if commands_dict[category] else "Keine Befehle in dieser Kategorie.",
                color=0x3498db
            )
            embed.set_image(
                url="https://www.pngall.com/wp-content/uploads/5/Help-PNG-Free-Image.png?text=HILFE"  # Breiteres Bild
            )
            embed.set_footer(
                text=f"Seite {page} von {total_pages}"
            )
            return embed

        embed = await generate_page(1)
        sent_message = await interaction.response.send_message(embed=embed, ephemeral=False)
        embed_message = await interaction.original_response()

        await embed_message.add_reaction("⬅️")
        await embed_message.add_reaction("➡️")

        def check(reaction, user):
            return (
                user == interaction.user
                and reaction.message.id == embed_message.id
                and str(reaction.emoji) in ["⬅️", "➡️"]
            )

        page = 1
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "➡️" and page < total_pages:
                    page += 1
                elif str(reaction.emoji) == "⬅️" and page > 1:
                    page -= 1

                await embed_message.edit(embed=await generate_page(page))
                try:
                    await reaction.remove(user)
                except discord.Forbidden:
                    pass
            except Exception:
                break


async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommands(bot))
