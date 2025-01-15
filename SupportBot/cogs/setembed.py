import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector
import json
import os


class SetEmbed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_connection = self.connect_to_database()

    def load_database_config(self):
        """Lädt die Datenbankkonfiguration aus der spezifischen `database_config.json`."""
        config_path = os.path.join(os.path.dirname(__file__), "../database_config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"❌ Konfigurationsdatei nicht gefunden: {config_path}")
        with open(config_path, "r") as file:
            return json.load(file)

    def connect_to_database(self):
        """Stellt die Verbindung zur MySQL-Datenbank her."""
        try:
            config = self.load_database_config()
            connection = mysql.connector.connect(
                host=config["host"],
                user=config["user"],
                password=config["password"],
                database=config["database"]
            )
            print("✅ Verbindung zur MySQL-Datenbank erfolgreich!")
            return connection
        except mysql.connector.Error as e:
            print(f"❌ Fehler bei der MySQL-Verbindung: {e}")
            return None

    @app_commands.command(name="setembed", description="Erstellt ein benutzerdefiniertes Embed.")
    async def set_embed(self, interaction: discord.Interaction):
        """Erstellt ein benutzerdefiniertes Embed basierend auf den Benutzereingaben."""
        modal = EmbedModal(self.bot, self.db_connection)
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
    def __init__(self, bot: commands.Bot, db_connection):
        super().__init__(title="Embed-Einstellungen")
        self.bot = bot
        self.db_connection = db_connection

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

        if image_url:
            embed.set_image(url=image_url)

        # Embed senden
        message = await interaction.channel.send(embed=embed)

        # Embed in der Datenbank speichern
        try:
            cursor = self.db_connection.cursor()
            query = """
            INSERT INTO embeds (message_id, channel_id, guild_id, title, description, color, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (message.id, interaction.channel.id, interaction.guild.id, title, description, str(color), image_url))
            self.db_connection.commit()
            cursor.close()
            await interaction.response.send_message(f"Embed wurde erfolgreich gesendet und gespeichert (Nachricht-ID: {message.id}).", ephemeral=True)
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler beim Speichern des Embeds in der Datenbank: {e}")
            await interaction.response.send_message("Ein Fehler ist aufgetreten. Das Embed konnte nicht gespeichert werden.", ephemeral=True)



async def setup(bot: commands.Bot):
    await bot.add_cog(SetEmbed(bot))
