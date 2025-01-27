import certifi
import discord
from discord.ext import commands, tasks
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
        self.webhook_url = os.getenv("WEBHOOK_URL")
        if not self.coc_api_token:
            raise ValueError("COC_API_TOKEN nicht in Umgebungsvariablen gesetzt.")
        if not self.webhook_url:
            raise ValueError("WEBHOOK_URL nicht in Umgebungsvariablen gesetzt.")
        self.db_connection = self.bot.db_connection
        self.update_verified_players.start()

    def get_headers(self):
        """Gibt die Header für die Clash-of-Clans-API zurück."""
        return {"Authorization": f"Bearer {self.coc_api_token}"}

    def get_verified_players(self):
        """Holt die verifizierten Spieler aus der Datenbank."""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT player_tag, coc_name FROM users")
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der verifizierten Spieler: {e}")
            return []

    def send_webhook_message(self, content: str):
        """Sendet eine Nachricht an den Webhook."""
        try:
            response = requests.post(self.webhook_url, json={"content": content})
            if response.status_code != 204:
                logger.error(f"Fehler beim Senden an den Webhook: {response.text}")
        except Exception as e:
            logger.error(f"Fehler beim Senden der Webhook-Nachricht: {e}")

    def get_player_data(self, player_tag: str) -> dict:
        """Holt die Spieler-Daten über die Clash of Clans API."""
        try:
            url = f"https://api.clashofclans.com/v1/players/{player_tag.replace('#', '%23')}"
            headers = {"Authorization": f"Bearer {os.getenv('COC_API_TOKEN')}"}
            response = requests.get(url, headers=headers, verify=certifi.where())
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen der Spieler-Daten: {response.status_code} - {response.text}")
                return None
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler bei der Verbindung zur API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unbekannter Fehler beim Abrufen der Spieler-Daten: {e}")
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

    @tasks.loop(hours=1)
    async def update_verified_players(self):
        """Aktualisiert die Liste der verifizierten Spieler."""
        required_clan_tag = os.getenv("REQUIRED_CLAN_TAG")
        if not required_clan_tag:
            logger.error("REQUIRED_CLAN_TAG nicht in Umgebungsvariablen gesetzt.")
            return

        # Clan-Daten abrufen
        url = f"{self.api_base_url}/clans/{required_clan_tag.replace('#', '%23')}/members"
        response = requests.get(url, headers=self.get_headers(), verify=certifi.where())
        if response.status_code != 200:
            logger.error(f"Fehler beim Abrufen der Clan-Mitglieder: {response.text}")
            return

        clan_members = {member["tag"]: member["name"] for member in response.json().get("items", [])}

        # Spieler in der Datenbank aktualisieren
        verified_players = self.get_verified_players()
        verified_tags = {player[0] for player in verified_players}

        # Entferne Spieler, die nicht mehr im Clan sind
        removed_players = [player for player in verified_players if player[0] not in clan_members]
        for player_tag, coc_name in removed_players:
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM users WHERE player_tag = %s", (player_tag,))
            self.db_connection.commit()
            cursor.close()
            self.send_webhook_message(f"**{player_tag} {coc_name}** wurde aus dem Clan entfernt.")

        # Füge neue Spieler hinzu
        for player_tag, coc_name in clan_members.items():
            if player_tag not in verified_tags:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                        INSERT INTO users (player_tag, coc_name, discord_id)
                        VALUES (%s, %s, NULL)
                    """, (player_tag, coc_name))
                self.db_connection.commit()
                cursor.close()
                self.send_webhook_message(f"**{player_tag} {coc_name}** wurde dem Clan hinzugefügt.")

    @app_commands.command(name="verify", description="Verifiziert einen Nutzer basierend auf seinem Spielertag.")
    async def verify(self, interaction: discord.Interaction, player_tag: str):
        """Verifiziert einen Nutzer basierend auf seinem Spielertag."""
        await interaction.response.defer(ephemeral=True)

        player_data = self.get_player_data(player_tag)
        if not player_data:
            await interaction.followup.send("Spieler-Daten konnten nicht abgerufen werden.", ephemeral=True)
            return

        coc_name = player_data.get("name", "Unbekannt")
        clan_data = player_data.get("clan", {})
        clan_tag = clan_data.get("tag")
        clan_name = clan_data.get("name")

        if not clan_tag:
            await interaction.followup.send("Spieler gehört keinem Clan an.", ephemeral=True)
            return

        required_clan_tag = os.getenv("REQUIRED_CLAN_TAG")
        if required_clan_tag and clan_tag != required_clan_tag:
            await interaction.followup.send(
                f"Spieler ist nicht im erforderlichen Clan ({required_clan_tag}).", ephemeral=True
            )
            return

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

        self.send_webhook_message(f"**{player_tag} {coc_name}** wurde erfolgreich verifiziert.")
        await interaction.followup.send(
            f"Erfolgreich als **{coc_name}** verifiziert. Spieler ist im Clan **{clan_name}**.", ephemeral=True
        )

    @app_commands.command(name="add_player", description="Fügt einen neuen Spieler manuell zur Datenbank hinzu.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_player(self, interaction: discord.Interaction, player_tag: str):
        """Fügt einen neuen Spieler basierend auf dem Spieler-Tag zur Datenbank hinzu."""
        try:
            # Überprüfen, ob der Spieler bereits existiert
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                SELECT * FROM users WHERE player_tag = %s
            """, (player_tag,))
            existing_player = cursor.fetchone()

            if existing_player:
                await interaction.response.send_message(f"Spieler mit dem Tag {player_tag} existiert bereits.",
                                                        ephemeral=True)
                return

            # Spielername über die API abrufen
            player_data = self.get_player_data(player_tag)
            if not player_data:
                await interaction.response.send_message(
                    f"Spieler mit dem Tag {player_tag} konnte nicht gefunden werden.", ephemeral=True
                )
                return

            coc_name = player_data.get("name")
            if not coc_name:
                await interaction.response.send_message(
                    f"Spielername für den Tag {player_tag} konnte nicht abgerufen werden.", ephemeral=True
                )
                return

            # Spieler in die Datenbank eintragen
            cursor.execute("""
                INSERT INTO users (player_tag, coc_name)
                VALUES (%s, %s)
            """, (player_tag, coc_name))
            self.bot.db_connection.commit()
            cursor.close()

            await interaction.response.send_message(
                f"Spieler **{coc_name}** mit Tag {player_tag} erfolgreich hinzugefügt.", ephemeral=True
            )
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen eines Spielers: {e}")
            await interaction.response.send_message("Fehler beim Hinzufügen des Spielers.", ephemeral=True)

    @app_commands.command(name="post_existing_players", description="Postet bereits eingetragene Spieler in den Channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def post_existing_players(self, interaction: discord.Interaction):
        """Postet alle verifizierten Spieler in den zugeordneten Channel."""
        try:
            players = self.get_verified_players()
            if not players:
                await interaction.response.send_message("Keine verifizierten Spieler gefunden.", ephemeral=True)
                return

            content = "**Verifizierte Spieler im Clan:**\n" + "\n".join(
                [f"**{tag} {name}**" for tag, name in players]
            )
            self.send_webhook_message(content)
            await interaction.response.send_message("Verifizierte Spieler wurden erfolgreich gepostet.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Posten der verifizierten Spieler: {e}")
            await interaction.response.send_message("Fehler beim Posten der Spieler.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Verification(bot))
