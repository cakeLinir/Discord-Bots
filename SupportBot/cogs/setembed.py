import asyncio

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

    async def is_authorized(self, interaction: discord.Interaction) -> bool:
        """Prüft, ob der Benutzer berechtigt ist."""
        support_users = self.config.get("support_users", [])
        support_roles = self.config.get("support_roles", [])

        # Debug-Ausgabe zur Überprüfung der Konfiguration
        print(f"[DEBUG] support_users: {support_users}")
        print(f"[DEBUG] support_roles: {support_roles}")

        if interaction.user.id in support_users:
            print(f"[DEBUG] Benutzer {interaction.user.id} ist autorisiert als Support-User.")
            return True

        user_roles = [role.id for role in interaction.user.roles]
        if any(role_id in support_roles for role_id in user_roles):
            print(f"[DEBUG] Benutzer {interaction.user.id} ist autorisiert basierend auf Rollen.")
            return True

        await interaction.response.send_message(
            "❌ Du hast keine Berechtigung, diesen Befehl auszuführen.",
            ephemeral=True
        )
        print(f"[DEBUG] Benutzer {interaction.user.id} ist nicht autorisiert.")
        return False

    @app_commands.command(name="setembed", description="Erstellt ein benutzerdefiniertes Embed in einem Kanal.")
    @app_commands.describe(channel_id="Die ID des Kanals, in den das Embed gesendet werden soll.")
    async def set_embed(self, interaction: discord.Interaction, channel_id: str):
        """Erstellt ein benutzerdefiniertes Embed basierend auf den Benutzereingaben."""
        if not await self.is_authorized(interaction):
            return

        try:
            channel_id = int(channel_id)
        except ValueError:
            await interaction.response.send_message(f"❌ `{channel_id}` ist keine gültige Kanal-ID.", ephemeral=True)
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(f"❌ Kanal mit ID {channel_id} nicht gefunden.", ephemeral=True)
            return

        modal = EmbedModal(self.bot, self.db_connection, channel)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="editembed",
                          description="Bearbeitet ein bestehendes Embed basierend auf der Nachricht-ID.")
    @app_commands.describe(message_id="Die ID der Nachricht, die bearbeitet werden soll.")
    async def edit_embed(self, interaction: discord.Interaction, message_id: str):
        """Bearbeitet ein bestehendes Embed."""
        # Datenbankprüfung
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            query = "SELECT * FROM embeds WHERE message_id = %s"
            cursor.execute(query, (message_id,))
            embed_data = cursor.fetchone()
            cursor.close()

            if not embed_data:
                await interaction.response.send_message(
                    f"❌ Keine Embed-Daten für Nachricht-ID {message_id}.", ephemeral=True
                )
                return
        except mysql.connector.Error as e:
            await interaction.response.send_message(f"❌ Fehler bei Datenbankzugriff: {e}", ephemeral=True)
            return

        # Kanal und Nachricht abrufen
        try:
            channel = self.bot.get_channel(int(embed_data["channel_id"]))
            if not channel:
                raise ValueError("Kanal nicht gefunden.")

            message = await channel.fetch_message(int(message_id))
        except Exception as e:
            await interaction.response.send_message(f"❌ Fehler beim Abrufen: {e}", ephemeral=True)
            return

        # Modal öffnen
        try:
            modal = EditEmbedModal(self.bot, self.db_connection, message, embed_data)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"[ERROR] Fehler beim Öffnen des Modals: {e}")
            await interaction.response.send_message("❌ Fehler beim Öffnen des Modals.", ephemeral=True)


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
        self.add_item(discord.ui.TextInput(
            label="Embed-Footer",
            placeholder="Footer des Embeds)",
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

class EditEmbedModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, db_connection, message, embed_data):
        super().__init__(title="Embed bearbeiten")
        self.bot = bot
        self.db_connection = db_connection
        self.message = message
        self.embed_data = embed_data

        # Titel
        self.title_input = discord.ui.TextInput(
            label="Titel",
            placeholder="Titel des Embeds",
            max_length=256
        )
        self.title_input.default = embed_data.get("title", "")  # Setze Standardwert
        self.add_item(self.title_input)

        # Beschreibung
        self.description_input = discord.ui.TextInput(
            label="Beschreibung",
            placeholder="Beschreibung des Embeds",
            style=discord.TextStyle.paragraph,
            max_length=2048
        )
        self.description_input.default = embed_data.get("description", "")  # Setze Standardwert
        self.add_item(self.description_input)

        # Farbe
        self.color_input = discord.ui.TextInput(
            label="Farbe (Hex-Wert, z. B. #3498db)",
            placeholder="Lass das leer für die Standardfarbe",
            required=False
        )
        self.color_input.default = embed_data.get("color", "")  # Setze Standardwert
        self.add_item(self.color_input)

        # Bild-URL
        self.image_input = discord.ui.TextInput(
            label="Bild-URL",
            placeholder="URL zu einem Bild für das Embed (Optional)",
            required=False
        )
        self.image_input.default = embed_data.get("image_url", "")  # Setze Standardwert
        self.add_item(self.image_input)

        self.footer_input = discord.ui.TextInput(
            label="Embed-Footer",
            placeholder="F",
            max_length=256
        )
        self.title_input.default = embed_data.get("title", "")  # Setze Standardwert
        self.add_item(self.title_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Bearbeitet das Embed basierend auf den Benutzereingaben."""
        title = self.title_input.value
        description = self.description_input.value
        color_input = self.color_input.value
        image_url = self.image_input.value

        # Farbe verarbeiten
        color = discord.Color.blue()
        if color_input:
            try:
                color = discord.Color(int(color_input.lstrip("#"), 16))
            except ValueError:
                await interaction.response.send_message("❌ Ungültiger Hex-Wert für die Farbe.", ephemeral=True)
                return

        # Aktualisiertes Embed erstellen
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        if image_url:
            embed.set_image(url=image_url)

        # Nachricht bearbeiten
        try:
            await self.message.edit(embed=embed)

            # Änderungen in der Datenbank speichern
            cursor = self.db_connection.cursor()
            query = """
            UPDATE embeds
            SET title = %s, description = %s, color = %s, image_url = %s
            WHERE message_id = %s
            """
            cursor.execute(query, (title, description, str(color), image_url, str(self.message.id)))
            self.db_connection.commit()
            cursor.close()

            await interaction.response.send_message(f"✅ Embed erfolgreich bearbeitet (Nachricht-ID: {self.message.id}).", ephemeral=True)
        except Exception as e:
            print(f"[ERROR] Fehler beim Bearbeiten des Embeds: {e}")
            await interaction.response.send_message("❌ Fehler beim Bearbeiten des Embeds.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SetEmbed(bot))
