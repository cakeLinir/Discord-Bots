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

    def build_war_embed(self, war_data: dict, page: int = 1) -> discord.Embed:
        """Erstellt ein Embed für die Clan-Kriegsdaten."""
        clan = war_data["clan"]
        opponent = war_data["opponent"]
        members = war_data["clan"]["members"] + war_data["opponent"]["members"]
        members_per_page = 10

        start_idx = (page - 1) * members_per_page
        end_idx = start_idx + members_per_page

        embed = discord.Embed(
            title=f"{clan['name']} :crossed_swords: {opponent['name']}",
            description=f"**Krieg: {clan['stars']} Sterne : {opponent['stars']} Sterne**",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Clan Sterne", value=f"{clan['stars']}", inline=True)
        embed.add_field(name="Gegner Sterne", value=f"{opponent['stars']}", inline=True)
        embed.add_field(name="Spieler pro Clan", value=f"{len(clan['members'])} vs {len(opponent['members'])}",
                        inline=True)

        # Hinzufügen der Spielerinformationen
        players_details = ""
        for member in members[start_idx:end_idx]:
            player_details = (
                f"**{member['name']}** (TH {member['townhallLevel']}) "
                f"**{member['stars']} Sterne**\n"
            )
            players_details += player_details

        embed.add_field(name="Spieler-Details", value=players_details or "Keine Spieler verfügbar", inline=False)
        embed.set_footer(text=f"Seite {page}/{(len(members) // members_per_page) + 1}")
        return embed

    async def send_paginated_war_embed(self, interaction: discord.Interaction, war_data: dict):
        """Sendet ein paginiertes Embed für den Clan-Krieg."""
        page = 1
        embed = self.build_war_embed(war_data, page)
        message = await interaction.response.send_message(embed=embed, ephemeral=True)

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        def check(reaction, user):
            return (
                    user == interaction.user
                    and str(reaction.emoji) in ["◀️", "▶️"]
                    and reaction.message.id == message.id
            )

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "▶️":
                    page += 1
                elif str(reaction.emoji) == "◀️":
                    page -= 1

                page = max(1, page)  # Seite darf nicht kleiner als 1 sein
                embed = self.build_war_embed(war_data, page)
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)
            except Exception:
                break

    @app_commands.command(name="ck_stats", description="Zeigt die aktuellen Clan-Krieg-Statistiken an.")
    async def ck_stats(self, interaction: discord.Interaction):
        """Holt die aktuellen Clan-Kriegsstatistiken und zeigt sie an."""
        try:
            clan_tag = os.getenv("CLAN_TAG")
            if not clan_tag:
                await interaction.response.send_message("Clan-Tag ist nicht gesetzt.", ephemeral=True)
                return

            war_data = self.fetch_current_war(clan_tag)
            if not war_data or war_data.get("state") != "inWar":
                await interaction.response.send_message("Kein laufender Clan-Krieg gefunden.", ephemeral=True)
                return

            await self.send_paginated_war_embed(interaction, war_data)
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Clan-Kriegsstatistiken: {e}")
            await interaction.response.send_message("Fehler beim Abrufen der Statistiken.", ephemeral=True)

    @app_commands.command(name="ck_private", description="Zeigt private Clan-Krieg-Statistiken an.")
    async def ck_private(self, interaction: discord.Interaction):
        """Holt die Clan-Kriegsstatistiken und zeigt sie nur dem User privat an."""
        await self.ck_stats(interaction)


async def setup(bot):
    await bot.add_cog(CK(bot))
