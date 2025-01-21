import discord
from discord.ext import commands
from discord import app_commands
import os
import aiohttp
import pymysql
from dotenv import load_dotenv
import logging

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Umgebungsvariablen laden
load_dotenv()

class TwitchCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        try:
            self.db_connection = pymysql.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("TWITCH_DB_NAME")
            )
        except pymysql.MySQLError as e:
            logger.error(f"Fehler bei der Verbindung zur Datenbank: {e}")
            self.db_connection = None

        self.twitch_client_id = os.getenv("TWITCH_CLIENT_ID")
        self.twitch_client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.twitch_token = None
        self.sent_messages = {}  # Speichert gesendete Nachrichten pro Streamer

    async def cog_unload(self):
        if self.session:
            await self.session.close()
        if self.db_connection:
            self.db_connection.close()

    async def get_twitch_token(self) -> str:
        """Holt ein Zugriffstoken von der Twitch API."""
        if self.twitch_token:
            return self.twitch_token

        url = "https://id.twitch.tv/oauth2/token"
        payload = {
            "client_id": self.twitch_client_id,
            "client_secret": self.twitch_client_secret,
            "grant_type": "client_credentials"
        }
        async with self.session.post(url, data=payload) as response:
            response_data = await response.json()
            if "access_token" not in response_data:
                logger.error("Fehler beim Abrufen des Twitch-Tokens: %s", response_data)
                raise ValueError("Kein Zugriffstoken erhalten.")
            self.twitch_token = response_data["access_token"]
            return self.twitch_token

    async def is_streamer_live(self, streamer_name: str) -> bool:
        """Überprüft, ob ein Streamer live ist."""
        token = await self.get_twitch_token()
        url = f"https://api.twitch.tv/helix/streams?user_login={streamer_name}"
        headers = {
            "Client-ID": self.twitch_client_id,
            "Authorization": f"Bearer {token}"
        }
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                logger.error(f"Fehler beim Überprüfen von {streamer_name}: {await response.text()}")
                return False
            data = await response.json()
            return len(data.get("data", [])) > 0

    async def get_stream_info(self, streamer_name: str) -> dict:
        """Holt Stream-Informationen von Twitch."""
        token = await self.get_twitch_token()
        url = f"https://api.twitch.tv/helix/streams?user_login={streamer_name}"
        headers = {
            "Client-ID": self.twitch_client_id,
            "Authorization": f"Bearer {token}"
        }
        async with self.session.get(url, headers=headers) as stream_response:
            if stream_response.status != 200:
                logger.error(f"Fehler beim Abrufen der Stream-Daten für {streamer_name}: {await stream_response.text()}")
                return None
            stream_data = await stream_response.json()
            if not stream_data.get("data"):
                return None

            stream_info = stream_data["data"][0]
            thumbnail = stream_info["thumbnail_url"].replace("{width}", "320").replace("{height}", "180")

        user_url = f"https://api.twitch.tv/helix/users?login={streamer_name}"
        async with self.session.get(user_url, headers=headers) as user_response:
            if user_response.status != 200:
                logger.error(f"Fehler beim Abrufen der User-Daten für {streamer_name}: {await user_response.text()}")
                return None
            user_data = await user_response.json()
            if not user_data.get("data"):
                return None

            user_info = user_data["data"][0]
            return {
                "title": stream_info["title"],
                "channel_name": user_info["display_name"],
                "channel_icon": user_info["profile_image_url"],
                "game": stream_info["game_name"],
                "viewer_count": stream_info["viewer_count"],
                "thumbnail": thumbnail,
                "channel_url": f"https://www.twitch.tv/{streamer_name}"
            }

    def add_streamer_to_db(self, streamer_name: str):
        """Fügt einen Streamer zur Datenbank hinzu."""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT 1 FROM streamers WHERE twitch_username = %s", (streamer_name,))
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Streamer {streamer_name} ist bereits in der Überwachungsliste.")

        cursor.execute(
            """
            INSERT INTO streamers (twitch_username)
            VALUES (%s)
            """,
            (streamer_name,)
        )
        self.db_connection.commit()
        cursor.close()

    def remove_streamer_from_db(self, streamer_name: str):
        """Entfernt einen Streamer aus der Datenbank."""
        cursor = self.db_connection.cursor()
        cursor.execute(
            """
            DELETE FROM streamers WHERE twitch_username = %s
            """,
            (streamer_name,)
        )
        self.db_connection.commit()
        cursor.close()

    def get_all_streamers(self):
        """Liest alle Streamer aus der Datenbank."""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT twitch_username FROM streamers")
        streamers = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return streamers

    def get_notification_channel(self) -> int:
        """Liest die Benachrichtigungskanal-ID aus der Datenbank."""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT channel_id FROM notification_channel LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else None

    def set_notification_channel(self, channel_id: int):
        """Speichert die Benachrichtigungskanal-ID in der Datenbank."""
        cursor = self.db_connection.cursor()
        cursor.execute(
            """
            INSERT INTO notification_channel (channel_id)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE channel_id = VALUES(channel_id)
            """,
            (channel_id,)
        )
        self.db_connection.commit()
        cursor.close()

    @app_commands.command(name="set_notification_channel", description="Setzt den Kanal für Twitch-Benachrichtigungen.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_notification_channel_command(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Setzt den Benachrichtigungskanal."""
        self.set_notification_channel(channel.id)
        await interaction.response.send_message(f"Benachrichtigungskanal wurde auf {channel.mention} gesetzt.", ephemeral=True)

    @app_commands.command(name="add_streamer", description="Fügt einen Streamer zur Überwachung hinzu.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_streamer(self, interaction: discord.Interaction, streamer_name: str):
        """Fügt einen Streamer zur Überwachungsliste hinzu."""
        if not await self.streamer_exists(streamer_name):
            await interaction.response.send_message(f"Streamer **{streamer_name}** existiert nicht auf Twitch.", ephemeral=True)
            return

        try:
            self.add_streamer_to_db(streamer_name)
            await interaction.response.send_message(f"Streamer **{streamer_name}** wurde zur Überwachungsliste hinzugefügt.", ephemeral=True)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)

    @app_commands.command(name="remove_streamer", description="Entfernt einen Streamer aus der Überwachungsliste.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_streamer(self, interaction: discord.Interaction, streamer_name: str):
        """Entfernt einen Streamer aus der Überwachungsliste."""
        self.remove_streamer_from_db(streamer_name)
        await interaction.response.send_message(f"Streamer **{streamer_name}** wurde aus der Überwachungsliste entfernt.", ephemeral=True)

    @app_commands.command(name="list_streamers", description="Listet alle überwachten Streamer auf.")
    async def list_streamers(self, interaction: discord.Interaction):
        """Listet alle Streamer auf, die überwacht werden."""
        streamers = self.get_all_streamers()
        if not streamers:
            await interaction.response.send_message("Es werden derzeit keine Streamer überwacht.", ephemeral=True)
        else:
            streamers_list = "\n".join(streamers)
            await interaction.response.send_message(f"Überwachte Streamer:\n{streamers_list}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TwitchCommands(bot))
