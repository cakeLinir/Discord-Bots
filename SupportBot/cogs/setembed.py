import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector
import json
import os


class SetEmbed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = self.load_config()
        self.db_connection = self.connect_to_database()
        self.initialize_database()

    def load_config(self):
        """Lädt die Konfigurationsdatei."""
        config_path = os.path.join(os.path.dirname(__file__), "../config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"❌ Konfigurationsdatei nicht gefunden: {config_path}")
        with open(config_path, "r") as file:
            return json.load(file)

    async def is_authorized(self, interaction: discord.Interaction) -> bool:
        """Prüft, ob der Benutzer berechtigt ist."""
        if interaction.user.id in self.config.get("support_users", []):
            return True
        if any(role.id in self.config.get("support_roles", []) for role in interaction.user.roles):
            return True

        await interaction.response.send_message(
            "❌ Du hast keine Berechtigung, diesen Befehl auszuführen.",
            ephemeral=True
        )
        return False

    def connect_to_database(self):
        """Stellt eine Verbindung zur MySQL-Datenbank her."""
        try:
            connection = mysql.connector.connect(
                host=self.config["db_host"],
                user=self.config["db_user"],
                password=self.config["db_password"],
                database=self.config["db_name"],
            )
            print("✅ Verbindung zur MySQL-Datenbank erfolgreich!")
            return connection
        except mysql.connector.Error as err:
            print(f"❌ Fehler bei der MySQL-Verbindung: {err}")
            raise

    def initialize_database(self):
        """Erstellt die Tabelle für Embeds, falls sie nicht existiert."""
        if self.db_connection:
            try:
                cursor = self.db_connection.cursor()
                query = """
                CREATE TABLE IF NOT EXISTS embeds (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    message_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    guild_id BIGINT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    color VARCHAR(7),
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                cursor.execute(query)
                self.db_connection.commit()
                cursor.close()
                print("✅ Tabelle 'embeds' erfolgreich initialisiert.")
            except mysql.connector.Error as e:
                print(f"❌ Fehler bei der Initialisierung der Tabelle 'embeds': {e}")

    @app_commands.command(name="setembed", description="Erstellt ein benutzerdefiniertes Embed in einem Kanal.")
    @app_commands.describe(channel_id="Die ID des Kanals, in den das Embed gesendet werden soll.")
    async def set_embed(self, interaction: discord.Interaction, channel_id: int):
        """Erstellt ein benutzerdefiniertes Embed basierend auf den Benutzereingaben."""
        if not await self.is_authorized(interaction):
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(f"❌ Kanal mit ID {channel_id} nicht gefunden.", ephemeral=True)
            return

        modal = EmbedModal(self.bot, self.db_connection, channel)
        await interaction.response.send_modal(modal)


class EmbedModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, db_connection, channel):
        super().__init__(title="Embed-Einstellungen")
        self.bot = bot
        self.db_connection = db_connection
        self.channel = channel

        self.add_item(discord.ui.TextInput(
            label="Titel",
            placeholder="Titel des Embeds",
            max_length=256
        ))
        self.add_item(discord.ui.TextInput(
            label="Beschreibung",
            placeholder="Beschreibung des Embeds",
            style=discord.TextStyle.paragraph,
            max_length=2048
        ))
        self.add_item(discord.ui.TextInput(
            label="Farbe (Hex-Wert, z. B. #3498db)",
            placeholder="Lass das leer für die Standardfarbe",
            required=False
        ))
        self.add_item(discord.ui.TextInput(
            label="Bild-URL",
            placeholder="URL zu einem Bild für das Embed (Optional)",
            required=False
        ))

    async def on_submit(self, interaction: discord.Interaction):
        """Speichert und sendet das Embed basierend auf Benutzereingaben."""
        title = self.children[0].value
        description = self.children[1].value
        color_input = self.children[2].value
        image_url = self.children[3].value

        color = discord.Color.blue()
        if color_input:
            try:
                color = discord.Color(int(color_input.lstrip("#"), 16))
            except ValueError:
                await interaction.response.send_message("❌ Ungültiger Hex-Wert für die Farbe.", ephemeral=True)
                return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        if image_url:
            embed.set_image(url=image_url)

        message = await self.channel.send(embed=embed)

        try:
            cursor = self.db_connection.cursor()
            query = """
            INSERT INTO embeds (message_id, channel_id, guild_id, title, description, color, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (message.id, self.channel.id, interaction.guild.id, title, description, str(color), image_url))
            self.db_connection.commit()
            cursor.close()
            await interaction.response.send_message(f"✅ Embed wurde erfolgreich gesendet und gespeichert (Nachricht-ID: {message.id}).", ephemeral=True)
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler beim Speichern des Embeds in der Datenbank: {e}")
            await interaction.response.send_message("❌ Fehler beim Speichern des Embeds.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SetEmbed(bot))
