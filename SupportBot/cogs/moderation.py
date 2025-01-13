import asyncio
import json

import discord
from discord.ext import commands, tasks
from discord import app_commands
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import os


def is_authorized():
    """Check, ob der Benutzer eine Supportrolle oder ein Supportuser ist."""
    async def predicate(interaction: discord.Interaction):
        cog = interaction.client.get_cog("AdminCog")
        if not cog:
            return False

        # Überprüfen der Rollen
        if interaction.user.id in cog.config.get("support_users", []):
            return True
        if any(role.id in cog.config.get("support_roles", []) for role in interaction.user.roles):
            return True

        # Wenn keine Berechtigung, Fehler werfen
        await interaction.response.send_message(
            "❌ Du hast keine Berechtigung, diesen Befehl auszuführen.",
            ephemeral=True
        )
        return False

    return app_commands.check(predicate)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.db_connection = self.connect_to_database()
        self.check_temp_bans.start()
        self.check_temp_mutes.start()

    def load_config(self):
        """Lädt die Konfigurationsdatei."""
        config_path = os.path.join(os.path.dirname(__file__), "../config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"❌ Konfigurationsdatei nicht gefunden: {config_path}")
        with open(config_path, "r") as file:
            return json.load(file)

    def save_config(self):
        """Speichert die Konfiguration."""
        config_path = os.path.join(os.path.dirname(__file__), "../config.json")
        with open(config_path, "w") as file:
            json.dump(self.config, file, indent=4)

    def connect_to_database(self):
        """Stellt eine Verbindung zur MySQL-Datenbank her."""
        try:
            connection = mysql.connector.connect(
                host=self.config["db_host"],
                user=self.config["db_user"],
                password=self.config["db_password"],
                database=self.config["db_name"],
            )
            print("✅ Verbindung zur MySQL-Datenbank erfolgreich!")
            return connection
        except Error as err:
            print(f"❌ Fehler bei der MySQL-Verbindung: {err}")
            raise

    def initialize_database(self):
        """Erstellt die notwendigen Tabellen für Moderationsaktionen."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS bans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                moderator_id BIGINT NOT NULL,
                reason TEXT,
                ban_type ENUM('permanent', 'temporary') NOT NULL,
                unban_at DATETIME DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mutes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                moderator_id BIGINT NOT NULL,
                reason TEXT,
                mute_type ENUM('permanent', 'temporary') NOT NULL,
                unmute_at DATETIME DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        cursor = self.db_connection.cursor()
        for query in queries:
            cursor.execute(query)
        self.db_connection.commit()

    @tasks.loop(seconds=60)  # Alle 60 Sekunden ausführen
    async def check_temp_mutes(self):
        """Überprüft regelmäßig, ob temporäre Mutes abgelaufen sind."""
        now = datetime.utcnow()
        cursor = self.db_connection.cursor(dictionary=True)
        try:
            # Temporäre Mutes abrufen, die abgelaufen sind
            query = "SELECT * FROM mutes WHERE unmute_at <= %s AND active = 1"
            cursor.execute(query, (now,))
            expired_mutes = cursor.fetchall()

            for mute in expired_mutes:
                guild = self.bot.get_guild(mute["guild_id"])
                member = guild.get_member(mute["user_id"])
                if member:
                    # Mute entfernen
                    muted_role = discord.utils.get(guild.roles, id=mute["role_id"])
                    if muted_role:
                        await member.remove_roles(muted_role, reason="Temporärer Mute abgelaufen")
                    # Datenbankeintrag aktualisieren
                    update_query = "UPDATE mutes SET active = 0 WHERE id = %s"
                    cursor.execute(update_query, (mute["id"],))
                    self.db_connection.commit()
                    print(f"[DEBUG] Mute für {member} wurde entfernt.")
        except Exception as e:
            print(f"[ERROR] Fehler bei check_temp_mutes: {e}")
        finally:
            cursor.close()

    @check_temp_mutes.before_loop
    async def before_check_temp_mutes(self):
        """Wartet, bis der Bot bereit ist, bevor die Schleife startet."""
        await self.bot.wait_until_ready()

    async def fetch_member(self, guild, identifier):
        """Holt ein Mitglied per ID oder Name."""
        try:
            if identifier.isdigit():
                return await guild.fetch_member(int(identifier))
            else:
                return discord.utils.get(guild.members, name=identifier)
        except Exception:
            return None

    def log_action(self, table, data):
        """Speichert eine Moderationsaktion in der Datenbank."""
        try:
            keys = ", ".join(data.keys())
            values = ", ".join(["%s"] * len(data))
            query = f"INSERT INTO {table} ({keys}) VALUES ({values})"
            cursor = self.db_connection.cursor()
            cursor.execute(query, tuple(data.values()))
            self.db_connection.commit()
            return cursor.lastrowid
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler beim Loggen der Aktion: {e}")
            return None

    @app_commands.command(name="ban", description="Bannt einen Benutzer permanent oder mit einem Grund.")
    @app_commands.describe(user="Die UserID oder der Nickname des Benutzers.", reason="Optional: Grund für den Bann.")
    @is_authorized()
    async def ban(self, interaction: discord.Interaction, user: str, reason: str = "Kein Grund angegeben"):
        """Bannt einen Benutzer dauerhaft."""
        member = await self.fetch_member(interaction.guild, user)
        if not member:
            await interaction.response.send_message("Benutzer nicht gefunden.", ephemeral=True)
            return

        try:
            await interaction.guild.ban(member, reason=reason)
            self.log_action("bans", {
                "user_id": member.id,
                "moderator_id": interaction.user.id,
                "reason": reason,
                "ban_type": "permanent"
            })
            await interaction.response.send_message(f"✅ {member.name} wurde permanent gebannt.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Fehler: {e}", ephemeral=True)

    @app_commands.command(name="temp_ban", description="Bannt einen Benutzer temporär.")
    @app_commands.describe(user="Die UserID oder der Nickname des Benutzers.", duration="Bann-Dauer in DD MM YYYY HH MM SS.", reason="Optional: Grund für den Bann.")
    @is_authorized()
    async def temp_ban(self, interaction: discord.Interaction, user: str, duration: str, reason: str = "Kein Grund angegeben"):
        """Bannt einen Benutzer temporär."""
        member = await self.fetch_member(interaction.guild, user)
        if not member:
            await interaction.response.send_message("Benutzer nicht gefunden.", ephemeral=True)
            return

        try:
            duration_parts = list(map(int, duration.split()))
            unban_time = datetime(*duration_parts)

            await interaction.guild.ban(member, reason=reason)
            self.log_action("bans", {
                "user_id": member.id,
                "moderator_id": interaction.user.id,
                "reason": reason,
                "ban_type": "temporary",
                "unban_at": unban_time
            })
            await interaction.response.send_message(f"✅ {member.name} wurde bis {unban_time} gebannt.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Fehler: {e}", ephemeral=True)

    @app_commands.command(name="unban", description="Entbannt einen Benutzer.")
    @app_commands.describe(user_id="Die UserID des Benutzers.")
    @is_authorized()
    async def unban(self, interaction: discord.Interaction, user_id: int):
        """Entbannt einen Benutzer."""
        try:
            banned_users = await interaction.guild.bans()
            user = discord.utils.get(banned_users, user__id=user_id)
            if not user:
                await interaction.response.send_message("Benutzer ist nicht gebannt.", ephemeral=True)
                return

            await interaction.guild.unban(user.user)
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM bans WHERE user_id = %s", (user_id,))
            self.db_connection.commit()
            await interaction.response.send_message(f"✅ {user.user.name} wurde entbannt.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Fehler: {e}", ephemeral=True)

    @tasks.loop(seconds=60)
    async def check_temp_bans(self):
        """Überprüft und hebt abgelaufene temporäre Banns auf."""
        now = datetime.utcnow()
        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bans WHERE ban_type = 'temporary' AND unban_at <= %s", (now,))
        expired_bans = cursor.fetchall()
        for ban in expired_bans:
            guild = self.bot.get_guild(ban["guild_id"])
            user = discord.Object(id=ban["user_id"])
            try:
                await guild.unban(user)
                cursor.execute("DELETE FROM bans WHERE id = %s", (ban["id"],))
                self.db_connection.commit()
                print(f"✅ Benutzer {ban['user_id']} wurde automatisch entbannt.")
            except Exception as e:
                print(f"[ERROR] Fehler beim automatischen Entbannen: {e}")
        cursor.close()


async def setup(bot):
    await bot.add_cog(Moderation(bot))
