import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import pymysql
import logging
from cryptography.fernet import Fernet
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_base_url = "https://api.clashofclans.com/v1"
        self.coc_api_token = os.getenv("COC_API_TOKEN")
        if not self.coc_api_token:
            raise ValueError("COC_API_TOKEN nicht in Umgebungsvariablen gesetzt.")
        self.db_connection = self.bot.db_connection

    def get_headers(self):
        """Gibt die Header für die Clash-of-Clans-API zurück."""
        return {"Authorization": f"Bearer {self.coc_api_token}"}

    def get_player_data(self, player_tag):
        """Holt die Spieler-Daten von der Clash-of-Clans-API."""
        url = f"{self.api_base_url}/players/{player_tag.replace('#', '%23')}"
        try:
            response = requests.get(url, headers=self.get_headers())
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen der Spieler-Daten: {response.text}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Spieler-Daten: {e}")
            return None

    def get_clan_data(self, clan_tag):
        """Holt die Clan-Daten von der Clash-of-Clans-API."""
        url = f"{self.api_base_url}/clans/{clan_tag.replace('#', '%23')}"
        try:
            response = requests.get(url, headers=self.get_headers())
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen der Clan-Daten: {response.text}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Clan-Daten: {e}")
            return None

    @app_commands.command(name="verify", description="Verifiziert einen Nutzer basierend auf seinem Spielertag.")
    async def verify(self, interaction: discord.Interaction, player_tag: str):
        """Verifiziert einen Nutzer basierend auf seinem Spielertag."""
        await interaction.response.defer(ephemeral=True)

        player_data = self.get_player_data(player_tag)
        if not player_data:
            await interaction.followup.send("Spieler-Daten konnten nicht abgerufen werden.", ephemeral=True)
            return

        # Spielername und Clan-Daten extrahieren
        coc_name = player_data.get("name", "Unbekannt")
        clan_data = player_data.get("clan", {})
        clan_tag = clan_data.get("tag")
        clan_name = clan_data.get("name")

        if not clan_tag:
            await interaction.followup.send("Spieler gehört keinem Clan an.", ephemeral=True)
            return

        # Überprüfen, ob der Spieler im vorgesehenen Clan ist
        required_clan_tag = os.getenv("REQUIRED_CLAN_TAG")  # Clan-Tag aus Umgebungsvariable
        if required_clan_tag and clan_tag != required_clan_tag:
            await interaction.followup.send(
                f"Spieler ist nicht im erforderlichen Clan ({required_clan_tag}).",
                ephemeral=True
            )
            return

        # Datenbank aktualisieren
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO users (discord_id, player_tag, coc_name, role)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE coc_name = VALUES(coc_name), role = VALUES(role)
            """, (interaction.user.id, player_tag, coc_name, player_data.get("role")))
            self.db_connection.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Datenbank: {e}")
            await interaction.followup.send("Datenbank-Fehler beim Verifizieren.", ephemeral=True)
            return

        # Erfolgreiche Verifizierung
        await interaction.followup.send(
            f"Erfolgreich als **{coc_name}** verifiziert. Spieler ist im Clan **{clan_name}** mit der Rolle **{player_data.get('role')}**.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Verification(bot))
