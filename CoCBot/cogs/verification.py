import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import pymysql
from cryptography.fernet import Fernet
import aiohttp
import logging
import ssl
import requests
import certifi


# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Umgebungsvariablen laden
load_dotenv()


class Verification(commands.Cog):
    def __init__(self, bot, session):
        self.bot = bot
        self.session = session  # Übernahme der Session vom Bot
        # Initialisiere die Datenbankverbindung
        try:
            self.db_connection = pymysql.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("COC_DB_NAME")
            )
        except pymysql.MySQLError as e:
            logger.error(f"Fehler bei der Verbindung zur Datenbank: {e}")
            self.db_connection = None

        # Verschlüsselungsschlüssel laden
        try:
            encryption_key = os.getenv("ENCRYPTION_KEY")
            if not encryption_key:
                raise ValueError("ENCRYPTION_KEY ist nicht gesetzt.")
            self.fernet = Fernet(encryption_key.encode())
        except Exception as e:
            logger.error(f"Fehler beim Laden des Verschlüsselungsschlüssels: {e}")
            raise

    async def cog_unload(self):
        """Schließe die Session und Datenbank bei Entladen der Cog."""
        if self.session:
            await self.session.close()
        if self.db_connection:
            self.db_connection.close()

    def encrypt_token(self, token):
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token):
        return self.fernet.decrypt(encrypted_token.encode()).decode()

    def get_clan_role(self, player_tag: str) -> tuple:
        """Holt die Clan-Rolle und den Clan-Tag eines Spielers."""
        try:
            url = f"https://api.clashofclans.com/v1/players/{player_tag.replace('#', '%23')}"
            headers = {"Authorization": f"Bearer {os.getenv('COC_API_TOKEN')}"}
            response = requests.get(url, headers=headers, verify=certifi.where())

            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen der Spieler-Daten: {response.status_code}, {response.text}")
                return None, None

            player_data = response.json()
            role = player_data.get("role", "Unknown")  # Standardwert
            clan_tag = player_data.get("clan", {}).get("tag", "NoClan")  # Standardwert

            logger.info(f"Von API zurückgegebene Clan-Rolle: {role}, Clan-Tag: {clan_tag}")
            return role, clan_tag
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Clan-Rolle: {e}")
            return None, None

    def get_discord_role_id(self, clan_role: str) -> int:
        """Holt die Discord-Rollen-ID für eine Clan-Rolle aus der Datenbank."""
        try:
            logger.info(f"Suche Discord-Rolle für Clan-Rolle: {clan_role}")
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT discord_role_id FROM clan_roles WHERE clan_role = %s", (clan_role,))
            result = cursor.fetchone()
            cursor.close()

            if result:
                logger.info(f"Gefundene Discord-Rolle-ID: {result[0]} für Clan-Rolle: {clan_role}")
                return result[0]
            else:
                logger.warning(f"Keine Discord-Rolle für Clan-Rolle '{clan_role}' gefunden.")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Discord-Rollen-ID: {e}")
            return None

    def add_user(self, discord_id: int, player_tag: str, encrypted_token: str, role: str):
        """Fügt einen Benutzer in die Datenbank ein."""
        if not role:
            raise ValueError("Die Rolle darf nicht leer sein.")

        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO users (discord_id, player_tag, encrypted_token, role)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE encrypted_token = VALUES(encrypted_token), role = VALUES(role)
            """, (discord_id, player_tag, encrypted_token or "EMPTY_TOKEN", role))  # Fallback für Token
            self.db_connection.commit()
            cursor.close()
            logger.info(f"Benutzer mit Discord-ID {discord_id} erfolgreich hinzugefügt oder aktualisiert.")
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Benutzers: {e}")

    def remove_user(self, discord_id: int) -> bool:
        """Entfernt einen Benutzer aus der Datenbank."""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM users WHERE discord_id = %s", (discord_id,))
            affected_rows = cursor.rowcount
            self.db_connection.commit()
            cursor.close()

            if affected_rows > 0:
                logger.info(f"Benutzer mit Discord-ID {discord_id} erfolgreich entfernt.")
                return True
            else:
                logger.warning(f"Benutzer mit Discord-ID {discord_id} nicht gefunden.")
                return False
        except Exception as e:
            logger.error(f"Fehler beim Entfernen des Benutzers: {e}")
            return False

    @app_commands.command(name="verify",
                          description="Verifiziert einen Nutzer und weist die passende Discord-Rolle zu.")
    async def verify(self, interaction: discord.Interaction, player_tag: str, token: str):
        """Verifiziert einen Nutzer und weist die passende Discord-Rolle zu."""
        try:
            # Sofortige Antwort, um die Interaktion zu bestätigen
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            # Spieler verifizieren und Clan-Rolle abrufen
            role, clan_tag = self.get_clan_role(player_tag)
            if not role:
                await interaction.followup.send(
                    "Die Rolle konnte nicht zugeordnet werden. Bitte überprüfe, ob du Mitglied eines Clans bist und die API korrekt konfiguriert ist.",
                    ephemeral=True
                )
                return

            # Discord-Rollen-ID abrufen
            discord_role_id = self.get_discord_role_id(role)
            if not discord_role_id:
                await interaction.followup.send(
                    f"Keine Discord-Rolle für Clan-Rolle '{role}' gefunden.",
                    ephemeral=True
                )
                return

            # Discord-Rolle zuweisen
            discord_role = interaction.guild.get_role(discord_role_id)
            if not discord_role:
                await interaction.followup.send(
                    f"Discord-Rolle mit ID {discord_role_id} nicht gefunden.",
                    ephemeral=True
                )
                return

            # Spieler und Token in die Datenbank einfügen
            encrypted_token = self.encrypt_token(token)
            self.add_user(interaction.user.id, player_tag, encrypted_token, role)

            # Rolle hinzufügen
            await interaction.user.add_roles(discord_role)
            logger.info(f"Rolle {discord_role.name} für {interaction.user} erfolgreich zugewiesen.")

            # Erfolgsmeldung
            await interaction.followup.send(
                f"Erfolgreich als **{role}** verifiziert und Rolle **{discord_role.name}** zugewiesen!",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Fehler beim Verifizieren: {e}")
            # Fehlernachricht nur senden, wenn noch keine Antwort erfolgt ist
            if not interaction.response.is_done():
                await interaction.followup.send("Fehler beim Verifizieren.", ephemeral=True)

    @app_commands.command(name="unverify", description="Entfernt deine Verifikation.")
    async def unverify(self, interaction: discord.Interaction):
        """Entfernt die Verifikation des Benutzers."""
        try:
            # Benutzer aus der Datenbank entfernen
            self.remove_user(interaction.user.id)

            # Liste der Rollen, die entfernt werden sollen
            roles_to_remove = ["Leader", "coLeader", "Elder", "Member"]
            removed_roles = []

            # Überprüfen, ob der Benutzer eine der Rollen hat
            for role_name in roles_to_remove:
                discord_role = discord.utils.get(interaction.guild.roles, name=role_name)
                if discord_role and discord_role in interaction.user.roles:
                    await interaction.user.remove_roles(discord_role)
                    removed_roles.append(discord_role.name)

            # Antwort basierend auf entfernten Rollen
            if removed_roles:
                removed_roles_list = ", ".join(removed_roles)
                message = f"Deine Verifikation wurde entfernt. Entfernte Rollen: {removed_roles_list}."
            else:
                message = "Deine Verifikation wurde entfernt. Es wurden keine zugeordneten Rollen gefunden."

            await interaction.response.send_message(message, ephemeral=True)

        except Exception as e:
            logger.error(f"Fehler beim Entfernen der Verifikation: {e}")
            await interaction.response.send_message("Fehler beim Entfernen der Verifikation.", ephemeral=True)

    @app_commands.command(name="set_clan_role", description="Verknüpft eine Clan-Rolle mit einer Discord-Rolle.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_clan_role(self, interaction: discord.Interaction, clan_role: str, discord_role: discord.Role):
        """Verknüpft eine Clan-Rolle mit einer Discord-Rolle."""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO clan_roles (clan_role, discord_role_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE discord_role_id = VALUES(discord_role_id)
            """, (clan_role, discord_role.id))
            self.db_connection.commit()
            cursor.close()

            await interaction.response.send_message(
                f"Clan-Rolle **{clan_role}** wurde mit Discord-Rolle **{discord_role.name}** verknüpft.",
                ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Verknüpfen der Clan-Rolle: {e}")
            await interaction.response.send_message("Fehler beim Verknüpfen der Clan-Rolle.", ephemeral=True)

async def setup(bot):
    session = aiohttp.ClientSession()
    await bot.add_cog(Verification(bot, session))
