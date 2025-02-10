import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import requests
import logging
import sqlite3

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.clashofclans.com/v1"
CLAN_TAG = os.getenv("CLAN_TAG")
COC_API_TOKEN = os.getenv("COC_API_TOKEN")
CLAN_ROLE_NAME = "Clan-Mitglied"
GUILD_ID = int(os.getenv("CLASH_GUILD_ID"))  # Guild ID aus .env

class Verification(commands.Cog):
    """Verifizierungssystem für Clan-Mitglieder."""

    def __init__(self, bot):
        self.bot = bot
        self.verify_clan_members.start()  # Automatische Überprüfung starten

    def cog_unload(self):
        """Stoppt die Überprüfung bei Cog-Unload."""
        self.verify_clan_members.cancel()

    def get_headers(self) -> dict:
        """Gibt die Header für die Clash of Clans API zurück."""
        return {"Authorization": f"Bearer {COC_API_TOKEN}"}

    def fetch_player_data(self, player_tag: str) -> dict:
        """Holt die Spieler-Daten von der Clash of Clans API."""
        try:
            url = f"{API_BASE_URL}/players/{player_tag.replace('#', '%23')}"
            response = requests.get(url, headers=self.get_headers())
            if response.status_code == 200:
                return response.json()
            logger.error(f"Fehler beim Abrufen der Spieler-Daten: {response.status_code} - {response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler bei der Verbindung zur API: {e}")
            return None

    def fetch_clan_members(self) -> list:
        """Holt die aktuellen Clan-Mitglieder von der Clash of Clans API."""
        try:
            url = f"{API_BASE_URL}/clans/{CLAN_TAG.replace('#', '%23')}"
            response = requests.get(url, headers=self.get_headers())
            if response.status_code == 200:
                return [member["tag"] for member in response.json().get("memberList", [])]
            logger.error(f"Fehler beim Abrufen der Clan-Daten: {response.status_code} - {response.text}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler bei der Verbindung zur API: {e}")
            return []

    @app_commands.command(name="verify", description="Verifiziert einen Spieler basierend auf seinem Spielertag.")
    @app_commands.guilds(GUILD_ID)
    async def verify(self, interaction: discord.Interaction, player_tag: str):
        """Verifiziert einen Spieler basierend auf seinem Spielertag."""
        await interaction.response.defer(ephemeral=True)

        player_data = self.fetch_player_data(player_tag)
        if not player_data:
            await interaction.followup.send("Spieler-Daten konnten nicht abgerufen werden.", ephemeral=True)
            return

        # Überprüfen, ob der Spieler im Clan ist
        clan_data = player_data.get("clan", {})
        if clan_data.get("tag") != CLAN_TAG:
            await interaction.followup.send("Dieser Spieler ist nicht im Clan.", ephemeral=True)
            return

        # Spieler in die Datenbank eintragen oder aktualisieren
        try:
            with sqlite3.connect("clash_bot.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO verified_players (discord_id, player_tag, coc_name)
                    VALUES (?, ?, ?)
                    ON CONFLICT(discord_id) 
                    DO UPDATE SET player_tag=excluded.player_tag, coc_name=excluded.coc_name
                    """,
                    (interaction.user.id, player_tag, player_data.get("name")),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Spielers in der Datenbank: {e}")
            await interaction.followup.send("Fehler beim Speichern des Spielers.", ephemeral=True)
            return

        # Rolle zuweisen
        role = discord.utils.get(interaction.guild.roles, name=CLAN_ROLE_NAME)
        if role:
            await interaction.user.add_roles(role)
            await interaction.followup.send(f"Du wurdest als **{player_data.get('name')}** verifiziert.", ephemeral=True)
        else:
            await interaction.followup.send("Rolle für Clan-Mitglieder nicht gefunden. Bitte kontaktiere einen Admin.", ephemeral=True)

    @tasks.loop(hours=24)
    async def verify_clan_members(self):
        """Überprüft täglich, ob verifizierte Mitglieder noch im Clan sind."""
        clan_members = self.fetch_clan_members()
        if not clan_members:
            logger.warning("Clan-Mitglieder konnten nicht abgerufen werden.")
            return

        try:
            with sqlite3.connect("clash_bot.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT discord_id, player_tag FROM verified_players")
                verified_players = cursor.fetchall()

                for discord_id, player_tag in verified_players:
                    member = self.bot.get_guild(GUILD_ID).get_member(discord_id)
                    if not member:
                        continue

                    # Entferne die Rolle, wenn der Spieler nicht mehr im Clan ist
                    if player_tag not in clan_members:
                        role = discord.utils.get(member.guild.roles, name=CLAN_ROLE_NAME)
                        if role and role in member.roles:
                            await member.remove_roles(role)
                            logger.info(f"Rolle für {member} entfernt (nicht mehr im Clan).")

                        # Spieler aus der Datenbank entfernen
                        cursor.execute("DELETE FROM verified_players WHERE player_tag = ?", (player_tag,))
                        conn.commit()
                        logger.info(f"{player_tag} wurde aus der Datenbank entfernt.")

        except Exception as e:
            logger.error(f"Fehler bei der Überprüfung der Clan-Mitglieder: {e}")

    @app_commands.command(name="check_clan", description="Überprüft alle verifizierten Spieler auf Mitgliedschaft.")
    @app_commands.guilds(GUILD_ID)
    async def check_clan(self, interaction: discord.Interaction):
        """Manuelle Überprüfung aller verifizierten Spieler."""
        await interaction.response.defer(ephemeral=True)
        await self.verify_clan_members()
        await interaction.followup.send("Überprüfung abgeschlossen.", ephemeral=True)

    async def cog_load(self):
        """Automatische Überprüfung starten, wenn das Cog geladen wird."""
        self.verify_clan_members.start()


async def setup(bot):
    await bot.add_cog(Verification(bot))
