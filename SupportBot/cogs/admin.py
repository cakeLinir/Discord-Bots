import discord
import json
import os
import mysql.connector
from mysql.connector import Error
from discord.ext import commands
from discord import app_commands


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = os.path.join(os.path.dirname(__file__), "../config.json")
        self.config = self.load_config()
        self.db_connection = self.connect_to_database()
        self.categories = {
            "menu": None,
            "erstellte": None,
            "uebernommen": None,
            "freigegeben": None,
            "geschlossen": None,
        }
        self.load_category_ids()

    def load_config(self):
        """Lädt die Konfiguration und stellt sicher, dass die notwendigen Felder existieren."""
        if not os.path.exists(self.config_path):
            initial_config = {
                "support_roles": [],
                "support_users": [],
                "support_channel_id": None,
                "categories": {},
            }
            with open(self.config_path, "w") as f:
                json.dump(initial_config, f, indent=4)
        with open(self.config_path, "r") as f:
            return json.load(f)

    def save_config(self):
        """Speichert die Konfiguration."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=4)

    async def is_authorized(self, interaction: discord.Interaction) -> bool:
        """Prüft, ob der Benutzer berechtigt ist."""
        support_users = self.config.get("support_users", [])
        support_roles = self.config.get("support_roles", [])

        # Debug-Ausgabe zur Überprüfung der Konfiguration
        print(f"[DEBUG] support_users: {support_users}")
        print(f"[DEBUG] support_roles: {support_roles}")

        if interaction.user.id in support_users:
            print(f"[DEBUG] Benutzer {interaction.user.id} ist autorisiert als Support-User.")
            return True

        user_roles = [role.id for role in interaction.user.roles]
        if any(role_id in support_roles for role_id in user_roles):
            print(f"[DEBUG] Benutzer {interaction.user.id} ist autorisiert basierend auf Rollen.")
            return True

        await interaction.response.send_message(
            "❌ Du hast keine Berechtigung, diesen Befehl auszuführen.",
            ephemeral=True
        )
        print(f"[DEBUG] Benutzer {interaction.user.id} ist nicht autorisiert.")
        return False

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

    def load_category_ids(self):
        """Lädt die gespeicherten Kategorien-IDs aus der Konfiguration."""
        self.categories.update(self.config.get("categories", {}))

    def save_category_ids(self):
        """Speichert die Kategorien-IDs in der Konfiguration."""
        self.config["categories"] = self.categories
        self.save_config()

    def update_ticket_status(self, ticket_id, status):
        """Aktualisiert den Status eines Tickets in der Datenbank."""
        try:
            query = "UPDATE tickets_new SET status = %s WHERE id = %s"
            cursor = self.db_connection.cursor()
            cursor.execute(query, (status, ticket_id))
            self.db_connection.commit()
            cursor.close()
            print(f"[DEBUG] Ticket {ticket_id} aktualisiert: {status}")
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler beim Aktualisieren des Ticket-Status: {e}")

    def fetch_ticket(self, ticket_id):
        """Holt ein Ticket aus der Datenbank."""
        try:
            query = "SELECT * FROM tickets_new WHERE id = %s"
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute(query, (ticket_id,))
            ticket = cursor.fetchone()
            cursor.close()
            return ticket
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler beim Abrufen des Tickets: {e}")
            return None

    def fetch_tickets_by_status(self, status):
        """Holt Tickets mit einem bestimmten Status aus der Datenbank."""
        try:
            query = "SELECT * FROM tickets_new WHERE status = %s"
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute(query, (status,))
            tickets = cursor.fetchall()
            cursor.close()
            return tickets
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler beim Abrufen der Tickets: {e}")
            return []

    async def move_ticket_to_category(self, guild, channel_id, category_id):
        """Verschiebt ein Ticket in eine bestimmte Kategorie."""
        channel = guild.get_channel(channel_id)
        category = guild.get_channel(category_id)
        if channel and category and isinstance(category, discord.CategoryChannel):
            await channel.edit(category=category)
            print(f"[DEBUG] Kanal {channel.name} in Kategorie {category.name} verschoben.")

    @app_commands.command(name="setup_ticket", description="Richtet das Ticketsystem ein.")
    async def setup_ticket(self, interaction: discord.Interaction):
        """Richtet das Ticketsystem ein."""
        guild = interaction.guild
        try:
            for name in self.categories.keys():
                category = discord.utils.get(guild.categories, id=self.categories.get(name))
                if not category:
                    category = await guild.create_category(f"✉️ {name.capitalize()}")
                    self.categories[name] = category.id
                    print(f"[DEBUG] Kategorie erstellt: {name.capitalize()} (ID: {category.id})")
            self.save_category_ids()
            await interaction.response.send_message("Das Ticketsystem wurde eingerichtet.", ephemeral=True)
        except Exception as e:
            print(f"[ERROR] Fehler bei setup_ticket: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)

    def load_config(self):
        """Lädt die Konfiguration und stellt sicher, dass die notwendigen Felder existieren."""
        if not os.path.exists(self.config_path):
            # Initiale Konfigurationsdatei erstellen, falls nicht vorhanden
            initial_config = {
                "support_roles": [],
                "support_users": [],
                "support_channel_id": None
            }
            with open(self.config_path, "w") as f:
                json.dump(initial_config, f, indent=4)
        with open(self.config_path, "r") as f:
            return json.load(f)

    def save_config(self):
        """Speichert die Konfiguration."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=4)

    @app_commands.command(name="add_support_role", description="Fügt eine Supportrolle hinzu.")
    @app_commands.describe(role_id="Die ID der hinzuzufügenden Rolle (als String).")
    async def add_support_role(self, interaction: discord.Interaction, role_id: str):
        """Fügt eine Supportrolle hinzu."""
        role_id = int(role_id)  # Konvertiere zu int für die interne Verarbeitung
        if role_id not in self.config["support_roles"]:
            self.config["support_roles"].append(role_id)
            self.save_config()
            await interaction.response.send_message(
                f"✅ Rolle mit ID {role_id} wurde als Supportrolle hinzugefügt.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Rolle mit ID {role_id} ist bereits eine Supportrolle.",
                ephemeral=True
            )

    @app_commands.command(name="remove_support_role", description="Entfernt eine Supportrolle.")
    @app_commands.describe(role_id="Die ID der zu entfernenden Rolle (als String).")
    async def remove_support_role(self, interaction: discord.Interaction, role_id: str):
        """Entfernt eine Supportrolle."""
        role_id = int(role_id)  # Konvertiere zu int
        if role_id in self.config["support_roles"]:
            self.config["support_roles"].remove(role_id)
            self.save_config()
            await interaction.response.send_message(
                f"✅ Rolle mit ID {role_id} wurde entfernt.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Rolle mit ID {role_id} ist keine Supportrolle.",
                ephemeral=True
            )

    @app_commands.command(name="add_support_user", description="Fügt einen Benutzer als Supporter hinzu.")
    @app_commands.describe(user_id="Die ID des hinzuzufügenden Benutzers (als String).")
    async def add_support_user(self, interaction: discord.Interaction, user_id: str):
        """Fügt einen Benutzer als Supporter hinzu."""
        user_id = int(user_id)  # Konvertiere zu int
        if user_id not in self.config["support_users"]:
            self.config["support_users"].append(user_id)
            self.save_config()
            await interaction.response.send_message(
                f"✅ Benutzer mit ID {user_id} wurde als Supporter hinzugefügt.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Benutzer mit ID {user_id} ist bereits ein Supporter.",
                ephemeral=True
            )

    @app_commands.command(name="remove_support_user", description="Entfernt einen Benutzer als Supporter.")
    @app_commands.describe(user_id="Die ID des zu entfernenden Benutzers (als String).")
    async def remove_support_user(self, interaction: discord.Interaction, user_id: str):
        """Entfernt einen Benutzer als Supporter."""
        user_id = int(user_id)  # Konvertiere zu int
        if user_id in self.config["support_users"]:
            self.config["support_users"].remove(user_id)
            self.save_config()
            await interaction.response.send_message(
                f"✅ Benutzer mit ID {user_id} wurde entfernt.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Benutzer mit ID {user_id} ist kein Supporter.",
                ephemeral=True
            )

    @app_commands.command(name="set_support_channel", description="Legt den Kanal für Support-Threads fest.")
    @app_commands.describe(channel_id="Die ID des Support-Kanals (als String).")
    async def set_support_channel(self, interaction: discord.Interaction, channel_id: str):
        """Legt den Kanal für Support-Threads fest."""
        channel_id = int(channel_id)  # Konvertiere zu int
        self.config["support_channel_id"] = channel_id
        self.save_config()
        await interaction.response.send_message(
            f"✅ Support-Kanal wurde auf ID {channel_id} gesetzt.",
            ephemeral=True
        )

    @app_commands.command(name="list_support_config", description="Listet die aktuelle Support-Konfiguration auf.")
    async def list_support_config(self, interaction: discord.Interaction):
        """Listet die aktuelle Support-Konfiguration auf."""

        # Rollen auflösen
        guild = interaction.guild
        resolved_roles = []
        for role_id in self.config.get("support_roles", []):
            role = guild.get_role(int(role_id))
            if role:
                resolved_roles.append(f"@{role.name} <@&{role.id}> {role.id}")
            else:
                resolved_roles.append(f"Unbekannte Rolle mit ID {role_id}")

        # Benutzer auflösen
        resolved_users = []
        for user_id in self.config.get("support_users", []):
            try:
                user = await self.bot.fetch_user(int(user_id))
                resolved_users.append(f"@{user.name}#{user.discriminator} <@{user.id}> {user.id}")
            except discord.NotFound:
                resolved_users.append(f"Unbekannter Benutzer mit ID {user_id}")

        # Support-Kanal auflösen
        support_channel_id = self.config.get("support_channel_id")
        support_channel = guild.get_channel(int(support_channel_id)) if support_channel_id else None
        resolved_channel = (
            f"#{support_channel.name} <#{support_channel.id}> {support_channel.id}"
            if support_channel
            else "Kein Kanal konfiguriert."
        )

        # Embed erstellen
        embed = discord.Embed(
            title="Aktuelle Support-Konfiguration",
            color=0x3498db
        )
        embed.add_field(name="Support-Rollen", value="\n".join(resolved_roles) or "Keine Rollen konfiguriert.",
                        inline=False)
        embed.add_field(name="Support-Benutzer", value="\n".join(resolved_users) or "Keine Benutzer konfiguriert.",
                        inline=False)
        embed.add_field(name="Support-Kanal", value=resolved_channel, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
