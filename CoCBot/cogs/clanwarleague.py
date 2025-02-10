import discord
from discord.ext import commands
from discord import app_commands
import os
import requests
import certifi
import logging
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

API_BASE_URL = "https://api.clashofclans.com/v1"

TOWNHALL_ICONS = {
    1: "<:th1:1333826242805497929>",
    2: "<:th2:1333826244461985878>",
    3: "<:th3:1333826246026723439>",
    4: "<:th4:1333826248006303804>",
    5: "<:th5:1333826249583497289>",
    6: "<:th6:1333826250854371419>",
    7: "<:th7:1333826252800397363>",
    8: "<:th8:1333826254553612351>",
    9: "<:th9:1333826256013234196>",
    10: "<:th10:1333826257657270445>",
    11: "<:th11:1333826547089543272>",
    12: "<:th12:1333826261688258653>",
    13: "<:th13:1333826548788367380>",
    14: "<:th14:1333826265463001190>",
    15: "<:th15:1333826550352576513>",
    16: "<:th16:1333826268730364087>",
    17: "<:th17:1333826552240017469>"
}

class CWL(commands.Cog):
    """Cog zur Verwaltung der CWL (Clan War League)."""

    def __init__(self, bot):
        self.bot = bot
        self.coc_api_token = os.getenv("COC_API_TOKEN")
        if not self.coc_api_token:
            raise ValueError("COC_API_TOKEN ist nicht in den Umgebungsvariablen gesetzt.")

    def get_headers(self) -> dict:
        """Headers für die Clash of Clans API."""
        return {"Authorization": f"Bearer {self.coc_api_token}"}

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await guild.fetch_channels()
        logger.info("Alle Kanäle wurden erfolgreich synchronisiert.")

    def get_stored_embed_data(self) -> dict:
        """Holt gespeicherte Embed-Daten aus der Datenbank für das CWL-Embed."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                SELECT message_id, channel_id FROM cwl_embed LIMIT 1
            """)
            result = cursor.fetchone()
            return {"message_id": result[0], "channel_id": result[1]} if result else None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der gespeicherten CWL-Embed-Daten: {e}")
        return None

    def save_embed_data(self, message_id: int, channel_id: int):
        """Speichert die Embed-Daten für CWL in der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                INSERT INTO cwl_embed (message_id, channel_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE message_id = VALUES(message_id), channel_id = VALUES(channel_id)
            """, (message_id, channel_id))
            self.bot.db_connection.commit()
        except Exception as e:
            logger.error(f"Fehler beim Speichern der CWL-Embed-Daten: {e}")

    @staticmethod
    def build_cwl_embed(war_data: dict, page: int, description: str = None) -> discord.Embed:
        """Erstellt ein Embed für die Clan-Krieg-Statistiken mit einem verbesserten Layout."""
        clan = war_data.get("clan", {})
        opponent = war_data.get("opponent", {})

        embed = discord.Embed(
            title=f"{clan.get('name', 'Unbekannt')} ⚔️ {opponent.get('name', 'Unbekannt')}",
            description=description or "Clan-Krieg-Liga-Statistiken",
            color=discord.Color.green()
        )

        # Spieler im aktuellen Page-Bereich
        start_index = (page - 1) * 10
        end_index = start_index + 10
        clan_members = clan.get("members", [])[start_index:end_index]
        opponent_members = opponent.get("members", [])[start_index:end_index]

        # Spieler-Daten formatieren
        clan_rows = []
        opponent_rows = []
        for clan_member, opponent_member in zip(clan_members, opponent_members):
            # Clan-Spieler
            clan_name = clan_member.get("name", "Unbekannt")
            clan_th_icon = TOWNHALL_ICONS.get(clan_member.get("townhallLevel"), "❓")
            clan_stars = clan_member.get("stars", 0)
            clan_attacks = len(clan_member.get("attacks", []))

            # Gegner-Spieler
            opponent_name = opponent_member.get("name", "Unbekannt")
            opponent_th_icon = TOWNHALL_ICONS.get(opponent_member.get("townhallLevel"), "❓")
            opponent_stars = opponent_member.get("stars", 0)
            opponent_attacks = len(opponent_member.get("attacks", []))

            # Zeilen formatieren
            clan_rows.append(f"{clan_name} {clan_th_icon} ⭐{clan_stars} ⚔️{clan_attacks}")
            opponent_rows.append(f"{opponent_name} {opponent_th_icon} ⭐{opponent_stars} ⚔️{opponent_attacks}")

        # Restliche Spieler auffüllen, falls ungleichmäßig
        if len(clan_members) > len(opponent_members):
            for clan_member in clan_members[len(opponent_members):]:
                clan_name = clan_member.get("name", "Unbekannt")
                clan_th_icon = TOWNHALL_ICONS.get(clan_member.get("townhallLevel"), "❓")
                clan_stars = clan_member.get("stars", 0)
                clan_attacks = len(clan_member.get("attacks", []))
                clan_rows.append(f"{clan_name} {clan_th_icon} ⭐{clan_stars} ⚔️{clan_attacks}")
                opponent_rows.append("-")

        elif len(opponent_members) > len(clan_members):
            for opponent_member in opponent_members[len(clan_members):]:
                opponent_name = opponent_member.get("name", "Unbekannt")
                opponent_th_icon = TOWNHALL_ICONS.get(opponent_member.get("townhallLevel"), "❓")
                opponent_stars = opponent_member.get("stars", 0)
                opponent_attacks = len(opponent_member.get("attacks", []))
                opponent_rows.append(f"{opponent_name} {opponent_th_icon} ⭐{opponent_stars} ⚔️{opponent_attacks}")
                clan_rows.append("-")

        # Tabellen-Inhalte
        clan_table = "\n".join(clan_rows)
        opponent_table = "\n".join(opponent_rows)

        # Tabellen in Embed hinzufügen
        embed.add_field(name="Clan", value=f"```{clan_table}```", inline=True)
        embed.add_field(name="Gegner", value=f"```{opponent_table}```", inline=True)

        # Footer mit Seitenangabe
        max_pages = (len(clan.get("members", [])) + 9) // 10
        embed.set_footer(text=f"Seite {page}/{max_pages}")
        return embed

    async def fetch_channel_by_id(self, channel_id: int) -> discord.TextChannel:
        """Erzwingt das Nachladen eines Kanals anhand seiner ID."""
        for guild in self.bot.guilds:
            try:
                channel = await guild.fetch_channel(channel_id)
                if channel:
                    logger.info(f"Kanal über API gefunden: {channel.name} (ID: {channel.id})")
                    return channel
            except discord.NotFound:
                continue
        logger.error(f"Kanal mit ID {channel_id} konnte nicht gefunden werden.")
        return None

    async def get_event_channel(self) -> discord.TextChannel:
        """Holt den Event-Channel für CWL aus der Datenbank und versucht, ihn direkt über die API abzurufen."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                SELECT channel_id FROM event_channels WHERE event_type = 'cwl'
            """)
            result = cursor.fetchone()
            if result:
                channel_id = int(result[0])
                logger.info(f"Abgerufene Kanal-ID aus der Datenbank: {channel_id}")

                # Prüfen, ob der Kanal im Cache ist
                channel = self.bot.get_channel(channel_id)
                if channel:
                    logger.info(f"Kanal aus Cache gefunden: {channel.name} (ID: {channel_id})")
                    return channel

                # Falls nicht im Cache, über API abrufen
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                    logger.info(f"Kanal über API gefunden: {channel.name} (ID: {channel_id})")
                    return channel
                except discord.NotFound:
                    logger.error(f"Kanal mit ID {channel_id} konnte nicht gefunden werden.")
                except discord.Forbidden:
                    logger.error(f"Bot hat keine Berechtigung für Kanal {channel_id}.")

        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Event-Channels: {e}")

        return None

    def fetch_current_event(self, clan_tag: str, is_cwl: bool = False) -> dict:
        """Holt die aktuellen Daten für Clan-Krieg oder CWL."""
        try:
            url = f"{API_BASE_URL}/clans/{clan_tag.replace('#', '%23')}/currentwarleaguegroup" if is_cwl else f"{API_BASE_URL}/clans/{clan_tag.replace('#', '%23')}/currentwar"
            response = requests.get(url, headers=self.get_headers(), verify=certifi.where())

            if response.status_code == 200:
                logger.info(f"Erfolgreich Daten abgerufen für {'CWL' if is_cwl else 'Clan-Krieg'}.")
                return response.json()
            elif response.status_code == 404:
                logger.info(f"Keine gültigen {'CWL' if is_cwl else 'Clan-Krieg'}-Daten gefunden (404).")
            else:
                logger.error(f"Fehler beim Abrufen der Daten: {response.status_code} - {response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler bei der Verbindung zur API: {e}")
            return None

    def fetch_current_warleaguegroup(self, clan_tag: str) -> dict:
        url = f"{API_BASE_URL}/clans/{clan_tag.replace('#', '%23')}/currentwarleaguegroup"
        return self._fetch_data(url, "CWL")

    async def post_or_update_cwl_embed(self):
        """Postet oder aktualisiert das Embed für die CWL."""
        try:
            clan_tag = os.getenv("CLAN_TAG")
            if not clan_tag:
                logger.error("Clan-Tag ist nicht gesetzt.")
                return

            cwl_data = self.fetch_current_event(clan_tag, is_cwl=True)
            if not cwl_data:
                logger.info("Keine gültigen CWL-Daten gefunden. Keine Aktion erforderlich.")
                return

            # Weitere Verarbeitung der CWL-Daten hier...
        except Exception as e:
            logger.error(f"Fehler beim Posten/Aktualisieren des CWL-Embeds: {e}")

    def process_cwl_data(self, clan_tag: str):
        """Prozessiert die CWL-Daten und gibt die Rundeninformationen zurück."""
        cwl_data = self.fetch_current_event(clan_tag, is_cwl=True)  # CWL-Daten abrufen
        if not cwl_data or "rounds" not in cwl_data:
            logger.info("Keine gültigen CWL-Daten gefunden.")
            return None

        rounds = cwl_data.get("rounds", [])
        if not rounds:
            logger.info("Keine Runden-Daten in der CWL gefunden.")
            return None

        logger.info(f"CWL-Daten erfolgreich verarbeitet: {len(rounds)} Runden gefunden.")
        return rounds

    @app_commands.command(name="cwl_refresh", description="Aktualisiert das CWL-Embed manuell.")
    async def cwl_refresh(self, interaction: discord.Interaction):
        """Manuelles Aktualisieren des CWL-Embeds."""
        try:
            await self.post_or_update_cwl_embed()
            await interaction.response.send_message("CWL-Embed wurde aktualisiert.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des CWL-Embeds: {e}")
            await interaction.response.send_message("Fehler beim Aktualisieren des CWL-Embeds.", ephemeral=True)

    async def cog_load(self):
        """Wird beim Laden des Cogs automatisch ausgeführt."""
        await self.post_or_update_cwl_embed()

async def setup(bot):
    await bot.add_cog(CWL(bot))
