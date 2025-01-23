import json

import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import certifi
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.clashofclans.com/v1"


class CoCAPI:
    def __init__(self):
        self.api_token = os.getenv("COC_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "API-Token nicht gesetzt. Bitte sicherstellen, dass die Umgebungsvariable 'COC_API_TOKEN' gesetzt ist.")

    def get_headers(self):
        """Gibt die Header für die API-Anfragen zurück."""
        return {"Authorization": f"Bearer {self.api_token}"}

    def fetch_clan_currentwar(self, clan_tag: str) -> dict:
        """Holt Daten für den aktuellen Clan-Krieg."""
        url = f"{API_BASE_URL}/clans/{clan_tag.replace('#', '%23')}/currentwar"
        try:
            response = requests.get(url, headers=self.get_headers(), verify=certifi.where())
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen von Clan-Kriegsdaten: {response.text}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen von Clan-Kriegsdaten: {e}")
            return None

    def fetch_clan_cwl(self, clan_tag: str) -> dict:
        """Holt Daten für die Clan-War-League."""
        url = f"{API_BASE_URL}/clans/{clan_tag.replace('#', '%23')}/currentwar/leaguegroup"
        try:
            response = requests.get(url, headers=self.get_headers(), verify=certifi.where())
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen von CWL-Daten: {response.text}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen von CWL-Daten: {e}")
            return None


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cwl_check.start()
        self.clanspiele_check.start()
        self.ck_check.start()

    def cog_unload(self):
        self.cwl_check.cancel()
        self.clanspiele_check.cancel()
        self.ck_check.cancel()

    @tasks.loop(hours=1)  # Alle 1 Stunde
    async def cwl_check(self):
        """Prüft CWL-Status und postet Updates."""
        try:
            data = self.get_event_data("CWL")  # Fiktive Funktion
            if data:
                channel = self.get_event_channel("CWL")
                if channel:
                    embed = self.build_event_embed("CWL", data)
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Fehler beim CWL-Check: {e}")

    @tasks.loop(hours=1)
    async def clanspiele_check(self):
        """Prüft Clan-Spiele-Status und postet Updates."""
        try:
            data = self.get_event_data("Clanspiele")  # Fiktive Funktion
            if data:
                channel = self.get_event_channel("Clanspiele")
                if channel:
                    embed = self.build_event_embed("Clanspiele", data)
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Fehler beim Clan-Spiele-Check: {e}")

    @tasks.loop(hours=1)
    async def ck_check(self):
        """Prüft CK-Status und postet Updates."""
        try:
            data = self.get_event_data("CK")  # Fiktive Funktion
            if data:
                channel = self.get_event_channel("CK")
                if channel:
                    embed = self.build_event_embed("CK", data)
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Fehler beim CK-Check: {e}")

    @cwl_check.before_loop
    @clanspiele_check.before_loop
    @ck_check.before_loop
    async def before_checks(self):
        """Warte, bis der Bot bereit ist."""
        await self.bot.wait_until_ready()

    def get_event_data(self, event_type: str) -> dict:
        """Holt die relevanten Daten von der API für das angegebene Event."""
        coc_api = CoCAPI()
        clan_tag = os.getenv("CLAN_TAG")  # Der Clan-Tag aus der Umgebungsvariable
        if not clan_tag:
            logger.error("CLAN_TAG nicht gesetzt. Bitte die Umgebungsvariable definieren.")
            return None
        if event_type == "Clanspiele":
            return self.get_clanspiele_data()
        elif event_type.lower() == "cwl":
            return coc_api.fetch_clan_cwl(clan_tag)
        elif event_type.lower() == "ck":
            return coc_api.fetch_clan_currentwar(clan_tag)
        else:
            logger.error(f"Unbekannter Event-Typ: {event_type}")
            return None

    def get_clanspiele_data(self) -> dict:
        """Holt die manuell eingetragenen Daten für Clanspiele aus der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                SELECT start_time, end_time, total_progress, member_progress 
                FROM clanspiele_data 
                ORDER BY id DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            cursor.close()

            if result:
                start_time, end_time, total_progress, member_progress_json = result

                # Konvertiere den JSON-String für Mitgliederfortschritt in ein Dictionary
                member_progress = json.loads(member_progress_json) if member_progress_json else {}

                return {
                    "start_time": start_time,
                    "end_time": end_time,
                    "total_progress": total_progress,
                    "member_progress": member_progress,
                }
            else:
                logger.warning("Keine Clanspiele-Daten in der Datenbank gefunden.")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Clanspiele-Daten: {e}")
            return None

    def get_event_channel(self, event_type: str) -> discord.TextChannel:
        """Holt den Discord-Kanal für ein Event aus der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("SELECT channel_id FROM event_channels WHERE event_type = %s", (event_type,))
            result = cursor.fetchone()
            cursor.close()
            if result:
                return self.bot.get_channel(int(result[0]))
            else:
                logger.warning(f"Kein Kanal für Event {event_type} konfiguriert.")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Kanals für {event_type}: {e}")
            return None

    def build_event_embed(self, event_type: str, data: dict) -> discord.Embed:
        """Erstellt ein Embed für das Event mit dynamischen Details."""
        embed = discord.Embed(
            title=f"{event_type} Update",
            description=f"Details zum {event_type}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="Start", value=data.get("start_time", "N/A"), inline=True)
        embed.add_field(name="Ende", value=data.get("end_time", "N/A"), inline=True)

        # Details dynamisch hinzufügen
        details = data.get("details", {})
        if isinstance(details, dict):  # JSON-Daten
            if event_type.lower() == "clanspiele":
                embed.add_field(name="Fortschritt", value=details.get("progress", "N/A"), inline=False)
                embed.add_field(name="Aufgaben", value=", ".join(details.get("tasks", [])), inline=False)
                embed.add_field(name="Belohnungen", value=", ".join(details.get("rewards", [])), inline=False)
            elif event_type.lower() == "cwl":
                embed.add_field(name="Gegner", value=details.get("opponents", "N/A"), inline=False)
                embed.add_field(name="Platzierung", value=details.get("placement", "N/A"), inline=False)
            elif event_type.lower() == "ck":
                embed.add_field(name="Angriffe", value=details.get("attacks", "N/A"), inline=False)
                embed.add_field(name="Spieler", value=", ".join(details.get("players", [])), inline=False)
        else:
            embed.add_field(name="Details", value=details, inline=False)

        embed.set_footer(text="Clash of Clans Events", icon_url="https://example.com/icon.png")
        return embed

    @app_commands.command(name="set_event_channel", description="Setzt den Discord-Kanal für ein Event.")
    @app_commands.choices(
        event_type=[
            app_commands.Choice(name="Clan-War-League (CWL)", value="cwl"),
            app_commands.Choice(name="Clan-Kriege (CK)", value="ck"),
            app_commands.Choice(name="Clan-Spiele", value="clanspiele"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_event_channel(self, interaction: discord.Interaction, event_type: app_commands.Choice[str],
                                channel: discord.TextChannel):
        """Setzt den Discord-Kanal für ein spezifisches Event."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                INSERT INTO event_channels (event_type, channel_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE channel_id = VALUES(channel_id)
            """, (event_type.value, channel.id))
            self.bot.db_connection.commit()
            cursor.close()

            await interaction.response.send_message(
                f"Der Kanal für **{event_type.name}** wurde erfolgreich auf {channel.mention} gesetzt.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Setzen des Event-Kanals: {e}")
            await interaction.response.send_message("Fehler beim Setzen des Kanals.", ephemeral=True)

    @app_commands.command(name="announce_event", description="Postet ein Event manuell.")
    @commands.has_permissions(administrator=True)
    async def announce_event(self, interaction: discord.Interaction, event_type: str):
        """Postet ein Event manuell."""
        try:
            data = self.get_event_data(event_type)
            if data:
                channel = self.get_event_channel(event_type)
                if channel:
                    embed = self.build_event_embed(event_type, data)
                    await channel.send(embed=embed)
                    await interaction.response.send_message(f"Event **{event_type}** wurde erfolgreich angekündigt.",
                                                            ephemeral=True)
                else:
                    await interaction.response.send_message(f"Kein Channel für Event {event_type} gesetzt.",
                                                            ephemeral=True)
            else:
                await interaction.response.send_message(f"Keine Daten für Event {event_type} gefunden.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Ankündigen des Events {event_type}: {e}")
            await interaction.response.send_message("Fehler beim Ankündigen des Events.", ephemeral=True)

    import discord
    from discord.ext import commands
    from discord import app_commands
    import logging
    import json
    from datetime import datetime

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    @app_commands.command(name="add_clanspiele_data", description="Fügt oder aktualisiert Clanspiele-Daten hinzu.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_clanspiele_data(
            self,
            interaction: discord.Interaction,
            start_time: str,
            end_time: str,
            progress: int,
            member_progress: str  # JSON-String: {"Player1": 1500, "Player2": 2000, ...}
    ):
        """Fügt Clanspiele-Daten hinzu oder aktualisiert bestehende."""
        try:
            # Clanspiele-Details vorbereiten
            total_progress = int(progress)
            member_progress_data = json.loads(member_progress)  # Erwartet JSON-String für Mitgliederfortschritt

            # Embed erstellen
            embed = self.build_clanspiele_embed(start_time, end_time, total_progress, member_progress_data)

            # Clanspiele-Kanal abrufen
            channel = self.get_event_channel("clanspiele")
            if not channel:
                await interaction.response.send_message(
                    "Kein Clanspiele-Kanal konfiguriert. Bitte zuerst den Kanal festlegen.",
                    ephemeral=True
                )
                return

            # Nachricht senden oder aktualisieren
            cursor = self.bot.db_connection.cursor()
            cursor.execute("SELECT message_id FROM clanspiele_data WHERE start_time = %s AND end_time = %s",
                           (start_time, end_time))
            result = cursor.fetchone()

            if result:
                # Nachricht aktualisieren
                message_id = result[0]
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
            else:
                # Neue Nachricht senden und ID speichern
                message = await channel.send(embed=embed)
                cursor.execute("""
                        INSERT INTO clanspiele_data (start_time, end_time, total_progress, member_progress, message_id, channel_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                    start_time, end_time, total_progress, json.dumps(member_progress_data), message.id, channel.id))
                self.bot.db_connection.commit()

            cursor.close()

            await interaction.response.send_message("Clan-Spiele-Daten erfolgreich hinzugefügt oder aktualisiert.",
                                                    ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Clanspiele-Daten: {e}")
            await interaction.response.send_message("Fehler beim Hinzufügen der Daten.", ephemeral=True)

    def build_clanspiele_embed(self, start_time: str, end_time: str, total_progress: int,
                               member_progress: dict) -> discord.Embed:
        """Erstellt ein Embed mit Clanspiele-Details."""
        embed = discord.Embed(
            title="Clan-Spiele Status",
            description="Aktueller Fortschritt der Clan-Spiele.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Startzeit", value=start_time, inline=True)
        embed.add_field(name="Endzeit", value=end_time, inline=True)
        embed.add_field(name="Gesamtfortschritt", value=f"{total_progress} / 50000 Punkte", inline=False)

        # Fortschrittsbalken für den Gesamtfortschritt
        progress_bar = self.generate_progress_bar(total_progress, 50000)
        embed.add_field(name="Fortschrittsbalken", value=progress_bar, inline=False)

        # Mitgliederfortschritt
        member_details = ""
        for member, points in member_progress.items():
            member_bar = self.generate_progress_bar(points, 4000)  # Maximale Punkte pro Mitglied
            member_details += f"**{member}:** {points} Punkte {member_bar}\n"

        embed.add_field(name="Mitgliederfortschritt", value=member_details, inline=False)
        embed.set_footer(text="Clash of Clans Bot - Clan-Spiele", icon_url="https://example.com/icon.png")
        return embed

    def generate_progress_bar(self, current: int, total: int, length: int = 20) -> str:
        """Erstellt einen Fortschrittsbalken."""
        filled_length = int(length * current // total)
        bar = "█" * filled_length + "-" * (length - filled_length)
        return f"`[{bar}]`"

    def get_event_channel(self, event_type: str) -> discord.TextChannel:
        """Holt den Discord-Channel für das Event."""
        try:
            channel_id = os.getenv(f"{event_type.upper()}_CHANNEL_ID")
            return self.bot.get_channel(int(channel_id)) if channel_id else None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Channels für {event_type}: {e}")
            return None


async def setup(bot):
    await bot.add_cog(Events(bot))
