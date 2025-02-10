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


class CK(commands.Cog):
    """Cog zur Verwaltung der Clan-Kriege."""

    def __init__(self, bot):
        self.bot = bot
        self.coc_api_token = os.getenv("COC_API_TOKEN")
        if not self.coc_api_token:
            raise ValueError("COC_API_TOKEN ist nicht in den Umgebungsvariablen gesetzt.")

    def get_headers(self) -> dict:
        """Headers für die Clash of Clans API."""
        return {"Authorization": f"Bearer {self.coc_api_token}"}

    def fetch_current_event(self, clan_tag: str, is_cwl: bool = False) -> dict:
        """
        Holt die aktuellen Daten für Clan-Krieg oder CWL basierend auf dem Parameter is_cwl.

        :param clan_tag: Das Clan-Tag des Clans.
        :param is_cwl: Wenn True, werden die CWL-Daten abgerufen. Ansonsten die CW-Daten.
        :return: Ein Dictionary mit den abgerufenen Daten oder None bei einem Fehler.
        """
        try:
            # URL basierend auf is_cwl bestimmen
            if is_cwl:
                url = f"{API_BASE_URL}/clans/{clan_tag.replace('#', '%23')}/currentwarleaguegroup"
                event_type = "CWL"
            else:
                url = f"{API_BASE_URL}/clans/{clan_tag.replace('#', '%23')}/currentwar"
                event_type = "Clan-Krieg"

            # Anfrage an die API senden
            response = requests.get(url, headers=self.get_headers(), verify=certifi.where())
            if response.status_code == 200:
                logger.info(f"{event_type}-Daten erfolgreich abgerufen.")
                return response.json()

            logger.error(f"Fehler beim Abrufen der {event_type}-Daten: {response.status_code} - {response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler bei der Verbindung zur API: {e}")
            return None

    def fetch_current_war(self, clan_tag: str) -> dict:
        """Holt die aktuellen Clan-Kriegsdaten von der API."""
        try:
            url = f"{API_BASE_URL}/clans/{clan_tag.replace('#', '%23')}/currentwar"
            response = requests.get(url, headers=self.get_headers(), verify=certifi.where())
            if response.status_code == 200:
                return response.json()
            logger.error(f"Fehler beim Abrufen der Clan-Kriegsdaten: {response.status_code} - {response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler bei der Verbindung zur API: {e}")
            return None

    async def fetch_channel_by_id(self, channel_id: int) -> discord.TextChannel:
        """Versucht, einen Kanal direkt über die Discord-API zu holen."""
        try:
            channel = await self.bot.fetch_channel(channel_id)
            logger.info(f"Kanal direkt gefunden: {channel.name} (ID: {channel_id})")
            return channel
        except discord.NotFound:
            logger.error(f"Kanal mit ID {channel_id} existiert nicht.")
        except discord.Forbidden:
            logger.error(f"Zugriff auf Kanal mit ID {channel_id} verweigert.")
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Kanals mit ID {channel_id}: {e}")
        return None

    async def get_event_channel(self) -> discord.TextChannel:
        """Holt den Event-Channel aus der Datenbank und versucht, ihn über die API abzurufen."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("SELECT channel_id FROM event_channels WHERE event_type = 'clan-war'")
            result = cursor.fetchone()
            if result:
                channel_id = int(result[0])
                logger.info(f"Abgerufene Kanal-ID aus der Datenbank: {channel_id}")

                # Prüfen, ob der Kanal im Cache verfügbar ist
                channel = self.bot.get_channel(channel_id)
                if channel:
                    logger.info(f"Kanal direkt aus Cache gefunden: {channel.name} (ID: {channel_id})")
                    return channel

                # Falls nicht im Cache, versuche den Kanal über die API zu laden
                logger.warning(f"Kanal mit ID {channel_id} nicht im Cache. Versuche, ihn über die API abzurufen.")
                for guild in self.bot.guilds:
                    try:
                        fetched_channel = await guild.fetch_channel(channel_id)
                        if fetched_channel:
                            logger.info(
                                f"Kanal erfolgreich über API gefunden: {fetched_channel.name} (ID: {channel_id})")
                            return fetched_channel
                    except discord.NotFound:
                        logger.warning(f"Kanal mit ID {channel_id} in {guild.name} nicht gefunden.")
                    except discord.Forbidden:
                        logger.error(
                            f"Bot hat keine Berechtigung, Kanal mit ID {channel_id} in {guild.name} abzurufen.")
                logger.error(f"Kanal mit ID {channel_id} konnte nicht gefunden werden.")
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Event-Channels: {e}")

        return None

    def get_stored_embed_data(self) -> dict:
        """Holt gespeicherte Embed-Daten aus der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                SELECT message_id, channel_id FROM clanwar_embed LIMIT 1
            """)
            result = cursor.fetchone()
            return {"message_id": result[0], "channel_id": result[1]} if result else None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Embed-Daten: {e}")
        return None

    def save_embed_data(self, message_id: int, channel_id: int):
        """Speichert die Embed-Daten in der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                INSERT INTO clanwar_embed (message_id, channel_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE message_id = VALUES(message_id), channel_id = VALUES(channel_id)
            """, (message_id, channel_id))
            self.bot.db_connection.commit()
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Embed-Daten: {e}")

    async def post_or_update_war_embed(self):
        """Postet oder aktualisiert das Embed für den aktuellen Clan-Krieg."""
        try:
            # Clan-Tag abrufen
            clan_tag = os.getenv("CLAN_TAG")
            if not clan_tag:
                logger.error("Clan-Tag ist nicht gesetzt.")
                return

            # Clan-Kriegsdaten abrufen
            war_data = self.fetch_current_event(clan_tag, is_cwl=False)
            if not war_data or war_data.get("state") not in ["inWar", "preparation"]:
                logger.info("Kein laufender oder vorbereitender Clan-Krieg gefunden.")
                return

            # Event-Channel abrufen
            event_channel = await self.get_event_channel()
            if not event_channel:
                logger.error("Event-Channel für Clan-Krieg nicht gefunden.")
                return

            # Beschreibung basierend auf dem Krieg-Zustand
            description = (
                "Der Clan-Krieg befindet sich in der **Vorbereitungsphase**. Spieler können Truppen in die Kriegsburgen spenden."
                if war_data.get("state") == "preparation"
                else "Der Clan-Krieg ist **aktiv**. Angriffe können durchgeführt werden."
            )

            # Embed erstellen
            embed = self.build_war_embed(war_data, page=1, description=description)

            # Überprüfen, ob ein Embed bereits existiert
            stored_embed_data = self.get_stored_embed_data()
            if stored_embed_data:
                try:
                    # Kanal abrufen (Cache oder API)
                    channel = self.bot.get_channel(stored_embed_data["channel_id"])
                    if channel is None:
                        # Kanal über API laden, falls nicht im Cache
                        for guild in self.bot.guilds:
                            try:
                                channel = await guild.fetch_channel(stored_embed_data["channel_id"])
                                if channel:
                                    logger.info(f"Kanal über API abgerufen: {channel.name} (ID: {channel.id})")
                                    break
                            except discord.NotFound:
                                continue
                    if channel is None:
                        logger.error(f"Kanal mit ID {stored_embed_data['channel_id']} nicht gefunden.")
                        return

                    # Nachricht abrufen und aktualisieren
                    message = await channel.fetch_message(stored_embed_data["message_id"])
                    if message:
                        await message.edit(embed=embed)
                        logger.info("Clan-Kriegs-Embed erfolgreich aktualisiert.")
                        return
                except discord.NotFound:
                    logger.warning("Vorheriges Embed nicht gefunden. Neues Embed wird erstellt.")

            # Neues Embed posten
            message = await event_channel.send(embed=embed)
            self.save_embed_data(message.id, event_channel.id)
            logger.info("Neues Clan-Kriegs-Embed gepostet und gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Posten/Aktualisieren des Clan-Kriegs-Embeds: {e}")

    @staticmethod
    def shorten_text(text: str, max_length: int = 1024) -> str:
        """Kürzt einen Text auf die maximale Länge."""
        if len(text) > max_length:
            return text[:max_length - 3] + "..."
        return text

    @staticmethod
    def build_war_embed(war_data: dict, page: int, description: str = None) -> discord.Embed:
        """Erstellt ein Embed für die Clan-Krieg-Statistiken mit Emojis für Townhalls."""
        clan = war_data.get("clan", {})
        opponent = war_data.get("opponent", {})

        embed = discord.Embed(
            title=f"{clan.get('name', 'Unbekannt')} ⚔️ {opponent.get('name', 'Unbekannt')}",
            description=description or "Clan-Krieg-Statistiken",
            color=discord.Color.blue()
        )

        # Spieler im aktuellen Page-Bereich
        start_index = (page - 1) * 10
        end_index = start_index + 10
        clan_members = clan.get("members", [])[start_index:end_index]
        opponent_members = opponent.get("members", [])[start_index:end_index]

        # Clan-Daten
        clan_rows = []
        for member in clan_members:
            name = member.get("name", "Unbekannt")
            townhall_icon = TOWNHALL_ICONS.get(member.get("townhallLevel"), "❓")
            stars = member.get("stars", 0)
            attacks = len(member.get("attacks", []))
            clan_rows.append(f"{name} {townhall_icon} ⭐{stars} ⚔️{attacks}")

        # Gegner-Daten
        opponent_rows = []
        for member in opponent_members:
            name = member.get("name", "Unbekannt")
            townhall_icon = TOWNHALL_ICONS.get(member.get("townhallLevel"), "❓")
            stars = member.get("stars", 0)
            attacks = len(member.get("attacks", []))
            opponent_rows.append(f"{name} {townhall_icon} ⭐{stars} ⚔️{attacks}")

        # Tabellen erstellen
        clan_table = "\n".join(clan_rows) or "Keine Spieler"
        opponent_table = "\n".join(opponent_rows) or "Keine Spieler"

        # Tabelle kürzen, falls sie zu lang ist
        clan_table = CK.shorten_text(clan_table)
        opponent_table = CK.shorten_text(opponent_table)

        # Tabelle ins Embed einfügen
        embed.add_field(name="Clan", value=f"{clan_table}", inline=True)
        embed.add_field(name="Gegner", value=f"{opponent_table}", inline=True)

        # Seiteninformation
        max_pages = (len(clan.get("members", [])) + 9) // 10
        embed.set_footer(text=f"Seite {page}/{max_pages}")
        return embed

    @app_commands.command(name="ck_private", description="Zeigt private Clan-Krieg-Statistiken an.")
    async def ck_private(self, interaction: discord.Interaction, page: int = 1):
        """Zeigt die Clan-Kriegsstatistiken privat für den Benutzer an."""
        try:
            clan_tag = os.getenv("CLAN_TAG")
            if not clan_tag:
                await interaction.response.send_message("Clan-Tag ist nicht gesetzt.", ephemeral=True)
                return

            war_data = self.fetch_current_war(clan_tag)
            if not war_data:
                await interaction.response.send_message("Es konnte kein Clan-Krieg gefunden werden.", ephemeral=True)
                return

            war_state = war_data.get("state")
            if war_state not in ["inWar", "preparation"]:
                await interaction.response.send_message(
                    f"Kein aktueller Krieg. Der Krieg befindet sich im Zustand: {war_state}.",
                    ephemeral=True
                )
                return

            description = (
                "Der Clan-Krieg befindet sich in der **Vorbereitungsphase**. Spieler können Truppen in die Kriegsburgen spenden."
                if war_state == "preparation"
                else "Der Clan-Krieg ist **aktiv**. Angriffe können durchgeführt werden."
            )

            # Berechnung der max. Seiten
            max_pages = (len(war_data["clan"]["members"]) + 9) // 10
            page = max(1, min(page, max_pages))

            # Embed erstellen
            embed = self.build_war_embed(war_data, page, description)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der privaten Clan-Krieg-Statistiken: {e}")
            await interaction.response.send_message("Fehler beim Abrufen der Statistiken.", ephemeral=True)

    @app_commands.command(name="ck_refresh", description="Aktualisiert das Clan-Kriegs-Embed manuell.")
    async def ck_refresh(self, interaction: discord.Interaction):
        """Manuelles Aktualisieren des Clan-Kriegs-Embeds."""
        try:
            await self.post_or_update_war_embed()
            await interaction.response.send_message("Clan-Kriegs-Embed wurde aktualisiert.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Clan-Kriegs-Embeds: {e}")
            await interaction.response.send_message("Fehler beim Aktualisieren des Embeds.", ephemeral=True)

    async def cog_load(self):
        """Automatisch ausführen beim Laden des Cogs."""
        await self.post_or_update_war_embed()

async def setup(bot):
    await bot.add_cog(CK(bot))
