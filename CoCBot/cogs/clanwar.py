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

async def setup(bot):
    await bot.add_cog(CK(bot))
