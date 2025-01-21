import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from TwitchNotifier.cogs.TwitchCommands import TwitchCommands
import os
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Umgebungsvariablen laden
load_dotenv()

class TwitchBot(commands.Bot):
    def __init__(self, token):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True  # Für App-Commands erforderlich

        super().__init__(command_prefix="/", intents=intents)
        self.token = token
        self.streamers = []  # Liste der zu überwachenden Streamer
        self.session = None  # HTTP-Session wird in `setup_hook` initialisiert
        self.sent_messages = {}  # Gesendete Nachrichten pro Streamer

    async def setup_hook(self):
        """Setup für den Bot."""
        print("Twitch Bot wird initialisiert...")

        # HTTP-Session initialisieren
        self.session = aiohttp.ClientSession()

        # Cogs hinzufügen
        await self.add_cog(TwitchCommands(self))

        # Slash-Commands synchronisieren
        synced = await self.tree.sync()
        print(f"Slash-Commands wurden synchronisiert: {len(synced)} von {len(self.tree.get_commands())} Commands.")
        for command in synced:
            print(f" - {command.name}: {command.description}")

        # Streamer aus der Datenbank laden
        await self.load_streamers_from_db()

        # Hintergrundtask starten
        self.check_twitch_streams.start()

    async def on_ready(self):
        """Event: Bot ist bereit."""
        print(f"{self.user} ist bereit und eingeloggt!")

    async def load_streamers_from_db(self):
        """Lädt die Streamer aus der Datenbank in die Liste."""
        cog = self.get_cog("TwitchCommands")
        if not cog:
            logger.error("Cog TwitchCommands nicht gefunden.")
            return

        # Alle Streamer aus der Datenbank abrufen
        self.streamers = cog.get_all_streamers()
        print(f"Geladene Streamer: {self.streamers}")

    async def close(self):
        """Schließt den Bot und die HTTP-Session."""
        if self.session:
            await self.session.close()
        await super().close()

    @tasks.loop(minutes=5)
    async def check_twitch_streams(self):
        """Überprüft alle 5 Minuten den Streaming-Status der Streamer."""
        print("Überprüfe Twitch-Streamer...")
        cog = self.get_cog("TwitchCommands")
        if not cog:
            logger.error("Cog TwitchCommands nicht gefunden. Breche Überprüfung ab.")
            return

        for streamer in self.streamers:
            print(f"Prüfe Streamer: {streamer}")
            try:
                live_status = await cog.is_streamer_live(streamer)
                print(f"Live-Status für {streamer}: {live_status}")

                if live_status:
                    stream_info = await cog.get_stream_info(streamer)
                    if stream_info:
                        print(f"Stream Info für {streamer}: {stream_info}")
                        # Nachricht senden oder aktualisieren
                        await self.send_or_update_notification(cog, streamer, stream_info)
                    else:
                        logger.error(f"Keine Stream-Informationen für {streamer} verfügbar.")
                else:
                    # Nachricht entfernen, wenn der Streamer offline geht
                    await self.remove_notification(cog, streamer)
            except Exception as e:
                logger.error(f"Fehler beim Überprüfen des Streamers {streamer}: {e}")

    async def send_or_update_notification(self, cog, streamer, stream_info):
        """Sendet oder aktualisiert die Benachrichtigung für einen Streamer."""
        channel_id = cog.get_notification_channel()
        if not channel_id:
            logger.error("Kein Benachrichtigungskanal gesetzt.")
            return

        channel = self.get_channel(channel_id)
        if not channel:
            logger.error(f"Kanal mit ID {channel_id} nicht gefunden oder keine Berechtigung.")
            return

        if streamer in self.sent_messages:
            # Nachricht aktualisieren
            message = self.sent_messages[streamer]
            try:
                await message.edit(embed=cog.build_embed(stream_info))
                logger.info(f"Nachricht für {streamer} aktualisiert.")
            except Exception as e:
                logger.error(f"Fehler beim Aktualisieren der Nachricht für {streamer}: {e}")
        else:
            # Neue Nachricht senden
            try:
                message = await channel.send(embed=cog.build_embed(stream_info), view=cog.build_view(stream_info))
                self.sent_messages[streamer] = message
                logger.info(f"Nachricht für {streamer} gesendet.")
            except Exception as e:
                logger.error(f"Fehler beim Senden der Nachricht für {streamer}: {e}")

    async def remove_notification(self, cog, streamer):
        """Entfernt eine Benachrichtigung, wenn der Streamer offline geht."""
        if streamer in self.sent_messages:
            try:
                message = self.sent_messages.pop(streamer)
                await message.delete()
                logger.info(f"Nachricht für {streamer} entfernt.")
            except Exception as e:
                logger.error(f"Fehler beim Entfernen der Nachricht für {streamer}: {e}")

    def start_bot(self):
        """Bot starten."""
        self.run(self.token)

# Falls diese Datei direkt ausgeführt wird
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN_TWITCH")
    if not token:
        raise ValueError("Kein Token für den Twitch Bot gefunden!")
    bot = TwitchBot(token)
    bot.start_bot()
