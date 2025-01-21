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
        self.sent_messages = {}  # Speichert gesendete Nachrichten für jeden Streamer

    async def cog_unload(self):
        if self.session:
            await self.session.close()
        if self.db_connection:
            self.db_connection.close()

    def get_all_streamers(self):
        """Liest alle Streamer aus der Datenbank."""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT twitch_username FROM streamers")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Streamer: {e}")
            return []
        finally:
            cursor.close()

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
            if not stream_data.get("data"):
                logger.warning(f"Streamer {streamer_name} ist nicht live oder Twitch hat keine Daten zurückgegeben.")
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

    def get_notification_channel(self) -> int:
        """Liest die Benachrichtigungskanal-ID aus der Datenbank."""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT channel_id FROM notification_channel LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else None

    def load_sent_messages(self):
        """Lädt die gesendeten Nachrichten aus der Datenbank."""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT streamer_name, message_id, channel_id FROM sent_notifications")
            rows = cursor.fetchall()
            for streamer_name, message_id, channel_id in rows:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = channel.fetch_message(message_id)
                    self.sent_messages[streamer_name] = message
            cursor.close()
            logger.info("Gesendete Nachrichten wurden erfolgreich geladen.")
        except Exception as e:
            logger.error(f"Fehler beim Laden der gesendeten Nachrichten: {e}")

    async def send_live_notification(self, streamer, stream_info):
        """Sendet oder aktualisiert eine Live-Benachrichtigung."""
        channel_id = self.get_notification_channel()
        if not channel_id:
            logger.error("Kein Benachrichtigungskanal gesetzt.")
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Kanal mit ID {channel_id} nicht gefunden.")
            return

        embed = self.build_embed(stream_info)
        view = self.build_view(stream_info)

        try:
            if streamer in self.sent_messages:
                # Nachricht aktualisieren
                message = self.sent_messages[streamer]
                await message.edit(embed=embed, view=view)
                logger.info(f"Nachricht für {streamer} aktualisiert.")
            else:
                # Neue Nachricht senden
                message = await channel.send(embed=embed, view=view)
                self.sent_messages[streamer] = message

                # Nachricht in der Datenbank speichern
                cursor = self.db_connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO sent_notifications (streamer_name, message_id, channel_id)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE message_id = VALUES(message_id), channel_id = VALUES(channel_id)
                    """,
                    (streamer, message.id, channel_id)
                )
                self.db_connection.commit()
                cursor.close()
                logger.info(f"Nachricht für {streamer} gesendet und gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Senden oder Aktualisieren der Nachricht für {streamer}: {e}")

    def build_embed(self, stream_info: dict) -> discord.Embed:
        """Erstellt ein Embed für den Live-Streamer."""
        embed = discord.Embed(
            title=f"{stream_info['channel_name']} ist live!",
            description=f"{stream_info['title']}\n\n[Zum Stream ansehen]({stream_info['channel_url']})",
            color=discord.Color.purple()
        )
        embed.set_author(name=stream_info["channel_name"], icon_url=stream_info["channel_icon"])
        embed.add_field(name="Spiel", value=stream_info["game"], inline=True)
        embed.add_field(name="Zuschauer", value=f"{stream_info['viewer_count']:,}", inline=True)
        embed.set_thumbnail(url=stream_info["channel_icon"])
        embed.set_image(url=stream_info["thumbnail"])
        embed.set_footer(
            text="Twitch",
            icon_url="https://static-00.iconduck.com/assets.00/twitch-icon-2048x2048-tipdihgh.png"
        )
        return embed

    def build_view(self, stream_info: dict) -> discord.ui.View:
        """Erstellt eine View mit einem Button zum Stream des Streamers."""
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="🔗 Zum Stream",
            url=stream_info["channel_url"],
            style=discord.ButtonStyle.link
        ))
        return view

    async def remove_notification(self, streamer):
        """Entfernt die Benachrichtigung für einen Streamer."""
        if streamer in self.sent_messages:
            try:
                message = self.sent_messages.pop(streamer)
                await message.delete()

                # Nachricht aus der Datenbank entfernen
                cursor = self.db_connection.cursor()
                cursor.execute(
                    "DELETE FROM sent_notifications WHERE streamer_name = %s",
                    (streamer,)
                )
                self.db_connection.commit()
                cursor.close()

                logger.info(f"Nachricht für {streamer} entfernt.")
            except Exception as e:
                logger.error(f"Fehler beim Entfernen der Nachricht für {streamer}: {e}")

    @app_commands.command(name="set_notification_channel", description="Setzt den Kanal für Twitch-Benachrichtigungen.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_notification_channel_command(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Setzt den Benachrichtigungskanal."""
        self.set_notification_channel(channel.id)
        await interaction.response.send_message(f"Benachrichtigungskanal wurde auf {channel.mention} gesetzt.",
                                                ephemeral=True)

    @app_commands.command(name="add_streamer", description="Fügt einen Streamer zur Überwachung hinzu.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_streamer(self, interaction: discord.Interaction, streamer_name: str):
        """Fügt einen Streamer zur Überwachungsliste hinzu."""
        if not await self.streamer_exists(streamer_name):
            await interaction.response.send_message(f"Streamer **{streamer_name}** existiert nicht auf Twitch.",
                                                    ephemeral=True)
            return

        try:
            self.add_streamer_to_db(streamer_name)
            await interaction.response.send_message(
                f"Streamer **{streamer_name}** wurde zur Überwachungsliste hinzugefügt.", ephemeral=True)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)

    @app_commands.command(name="remove_streamer", description="Entfernt einen Streamer aus der Überwachungsliste.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_streamer(self, interaction: discord.Interaction, streamer_name: str):
        """Entfernt einen Streamer aus der Überwachungsliste."""
        self.remove_streamer_from_db(streamer_name)
        await interaction.response.send_message(
            f"Streamer **{streamer_name}** wurde aus der Überwachungsliste entfernt.", ephemeral=True)

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
