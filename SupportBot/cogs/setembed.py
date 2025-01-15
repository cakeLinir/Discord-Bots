import discord
from discord.ext import commands
from discord import app_commands

class SetEmbed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setembed", description="Erstellt ein benutzerdefiniertes Embed.")
    async def set_embed(self, interaction: discord.Interaction):
        """Erstellt ein benutzerdefiniertes Embed basierend auf den Benutzereingaben."""
        # Beispiel für eine Vorlage
        modal = EmbedModal(self.bot)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="affiliate_embed", description="Erstellt ein Embed mit einem Affiliate-Link und Bild.")
    async def affiliate_embed(self, interaction: discord.Interaction):
        """Erstellt ein Embed mit einem Bild und einem Affiliate-Link."""
        embed = discord.Embed(
            title="ZAP-Hosting Gameserver and Webhosting",
            description="[Klicke hier, um ZAP-Hosting zu besuchen](https://zap-hosting.com/hundekuchen)",
            color=0x3498db
        )
        embed.set_image(url="https://zap-hosting.com/interface/download/images.php?type=affiliate&id=408992")
        embed.set_footer(text="Unterstütze uns durch die Nutzung des Links!")
        await interaction.response.send_message(embed=embed)

class EmbedModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot):
        super().__init__(title="Embed-Einstellungen")
        self.bot = bot

        # Titel-Eingabe
        self.add_item(discord.ui.TextInput(
            label="Titel",
            placeholder="Titel des Embeds",
            max_length=256
        ))

        # Beschreibung-Eingabe
        self.add_item(discord.ui.TextInput(
            label="Beschreibung",
            placeholder="Beschreibung des Embeds",
            style=discord.TextStyle.paragraph,
            max_length=2048
        ))

        # Farbe-Eingabe (Optional)
        self.add_item(discord.ui.TextInput(
            label="Farbe (Hex-Wert, z. B. #3498db)",
            placeholder="Lass das leer für die Standardfarbe",
            required=False
        ))

        # Bild-URL (Optional)
        self.add_item(discord.ui.TextInput(
            label="Bild-URL",
            placeholder="URL zu einem Bild für das Embed (Optional)",
            required=False
        ))

    async def on_submit(self, interaction: discord.Interaction):
        """Wird aufgerufen, wenn der Benutzer die Modal-Eingaben absendet."""
        title = self.children[0].value
        description = self.children[1].value
        color_input = self.children[2].value
        image_url = self.children[3].value

        # Standardfarbe verwenden, wenn keine Farbe angegeben wurde
        color = discord.Color.blue()  # Standardfarbe
        if color_input:
            try:
                color = discord.Color(int(color_input.lstrip("#"), 16))
            except ValueError:
                await interaction.response.send_message("Ungültiger Hex-Wert für die Farbe.", ephemeral=True)
                return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        # Optional: Bild hinzufügen
        if image_url:
            embed.set_image(url=image_url)

        # Embed senden
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(SetEmbed(bot))
