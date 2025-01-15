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

    def is_authorized(self, interaction: discord.Interaction) -> bool:
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
    @app_commands.describe(role_id="Die ID der hinzuzufügenden Rolle.")
    async def add_support_role(self, interaction: discord.Interaction, role_id: int):
        """Fügt eine Supportrolle hinzu."""
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
    @app_commands.describe(role_id="Die ID der zu entfernenden Rolle.")
    async def remove_support_role(self, interaction: discord.Interaction, role_id: int):
        """Entfernt eine Supportrolle."""
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
    @app_commands.describe(user_id="Die ID des hinzuzufügenden Benutzers.")
    async def add_support_user(self, interaction: discord.Interaction, user_id: int):
        """Fügt einen Benutzer als Supporter hinzu."""
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
    @app_commands.describe(user_id="Die ID des zu entfernenden Benutzers.")
    async def remove_support_user(self, interaction: discord.Interaction, user_id: int):
        """Entfernt einen Benutzer als Supporter."""
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
    @app_commands.describe(channel_id="Die ID des Support-Kanals.")
    async def set_support_channel(self, interaction: discord.Interaction, channel_id: int):
        """Legt den Kanal für Support-Threads fest."""
        self.config["support_channel_id"] = channel_id
        self.save_config()
        await interaction.response.send_message(
            f"✅ Support-Kanal wurde auf ID {channel_id} gesetzt.",
            ephemeral=True
        )

    @app_commands.command(name="list_support_config", description="Listet die aktuelle Support-Konfiguration auf.")
    async def list_support_config(self, interaction: discord.Interaction):
        """Listet die aktuelle Support-Konfiguration auf."""
        support_roles = "\n".join(map(str, self.config["support_roles"])) or "Keine Rollen konfiguriert."
        support_users = "\n".join(map(str, self.config["support_users"])) or "Keine Benutzer konfiguriert."
        support_channel = self.config["support_channel_id"] or "Kein Kanal konfiguriert."

        embed = discord.Embed(
            title="Aktuelle Support-Konfiguration",
            color=0x3498db
        )
        embed.add_field(name="Support-Rollen", value=support_roles, inline=False)
        embed.add_field(name="Support-Benutzer", value=support_users, inline=False)
        embed.add_field(name="Support-Kanal", value=support_channel, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

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

    @app_commands.command(name="claim_ticket",
                          description="Beansprucht ein Ticket und verschiebt es in die Übernommen-Kategorie.")
    @app_commands.describe(ticket_id="Die ID des Tickets, das beansprucht werden soll.")
    async def claim_ticket(self, interaction: discord.Interaction, ticket_id: int):
        """Beansprucht ein Ticket."""
        ticket = self.fetch_ticket(ticket_id)
        if not ticket:
            await interaction.response.send_message("❌ Ticket nicht gefunden.", ephemeral=True)
            return

        guild = interaction.guild
        uebernommen_category_id = self.categories.get("uebernommen")
        await self.move_ticket_to_category(guild, ticket["channel_id"], uebernommen_category_id)
        self.update_ticket_status(ticket_id, "claimed")
        await interaction.response.send_message(f"✅ Ticket {ticket_id} wurde beansprucht.", ephemeral=True)

    @app_commands.command(name="release_ticket",
                          description="Gibt ein beanspruchtes Ticket frei und verschiebt es in die Freigegeben-Kategorie.")
    @app_commands.describe(ticket_id="Die ID des Tickets, das freigegeben werden soll.")
    async def release_ticket(self, interaction: discord.Interaction, ticket_id: int):
        """Gibt ein Ticket frei."""
        ticket = self.fetch_ticket(ticket_id)
        if not ticket:
            await interaction.response.send_message("❌ Ticket nicht gefunden.", ephemeral=True)
            return

        guild = interaction.guild
        freigegeben_category_id = self.categories.get("freigegeben")
        await self.move_ticket_to_category(guild, ticket["channel_id"], freigegeben_category_id)
        self.update_ticket_status(ticket_id, "released")
        await interaction.response.send_message(f"✅ Ticket {ticket_id} wurde freigegeben.", ephemeral=True)

    @app_commands.command(name="close_ticket",
                          description="Schließt ein Ticket und verschiebt es in die Geschlossen-Kategorie.")
    @app_commands.describe(ticket_id="Die ID des Tickets, das geschlossen werden soll.")
    async def close_ticket(self, interaction: discord.Interaction, ticket_id: int):
        """Schließt ein Ticket."""
        ticket = self.fetch_ticket(ticket_id)
        if not ticket:
            await interaction.response.send_message("❌ Ticket nicht gefunden.", ephemeral=True)
            return

        guild = interaction.guild
        geschlossen_category_id = self.categories.get("geschlossen")
        await self.move_ticket_to_category(guild, ticket["channel_id"], geschlossen_category_id)
        self.update_ticket_status(ticket_id, "closed")
        await interaction.response.send_message(f"✅ Ticket {ticket_id} wurde geschlossen.", ephemeral=True)

    @app_commands.command(name="ticket_list", description="Listet alle Tickets eines bestimmten Status auf.")
    @app_commands.describe(status="Der Status der Tickets: open, claimed, released, closed.")
    async def ticket_list(self, interaction: discord.Interaction, status: str):
        """Listet alle Tickets mit einem bestimmten Status auf."""
        valid_statuses = ["open", "claimed", "released", "closed"]
        if status not in valid_statuses:
            await interaction.response.send_message(f"❌ Ungültiger Status. Gültige Werte: {', '.join(valid_statuses)}",
                                                    ephemeral=True)
            return

        tickets = self.fetch_tickets_by_status(status)
        if not tickets:
            await interaction.response.send_message(f"Keine Tickets mit dem Status '{status}' gefunden.",
                                                    ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Tickets mit Status '{status}'",
            color=0x3498db
        )
        for ticket in tickets:
            embed.add_field(
                name=f"Ticket ID: {ticket['id']}",
                value=f"Channel: {ticket['channel_name']} | User ID: {ticket['user_id']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
