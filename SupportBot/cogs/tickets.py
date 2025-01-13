import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import mysql.connector
from mysql.connector import Error


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.categories = {
            "menu": None,
            "erstellte": None,
            "uebernommen": None,
            "freigegeben": None,
            "geschlossen": None,
        }
        self.db_connection = self.connect_to_database()
        self.initialize_database()

        # Lade Kategorien-IDs aus der Konfiguration
        self.load_category_ids()

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
        """Erstellt die Tabelle für Tickets."""
        query = """
        CREATE TABLE IF NOT EXISTS tickets_new (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            channel_id BIGINT NOT NULL,
            channel_name VARCHAR(255),
            status ENUM('open', 'claimed', 'released', 'closed') DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor = self.db_connection.cursor()
        cursor.execute(query)
        self.db_connection.commit()

    def load_category_ids(self):
        """Lädt die gespeicherten Kategorien-IDs aus der Konfiguration."""
        for category in self.categories.keys():
            category_id = self.config.get(f"{category}_id")
            if category_id:
                self.categories[category] = category_id

    def save_category_ids(self):
        """Speichert die Kategorien-IDs in der Konfiguration."""
        for name, category_id in self.categories.items():
            if category_id:
                self.config[f"{name}_id"] = category_id
        self.save_config()

    def create_ticket(self, user_id, channel_id, channel_name, message=None):
        """Speichert ein neues Ticket in der Datenbank und gibt die Ticket-ID zurück."""
        try:
            query = """
            INSERT INTO tickets_new (user_id, channel_id, channel_name, message)
            VALUES (%s, %s, %s, %s)
            """
            cursor = self.db_connection.cursor()
            cursor.execute(query, (user_id, channel_id, channel_name, message))
            self.db_connection.commit()
            ticket_id = cursor.lastrowid  # Automatisch generierte ID abrufen
            cursor.close()
            return ticket_id
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler bei create_ticket: {e}")
            return None

    def update_ticket_channel(self, ticket_id, channel_id, channel_name):
        """Aktualisiert die Kanal-ID und den Namen eines Tickets in der Datenbank."""
        try:
            query = """
            UPDATE tickets_new
            SET channel_id = %s, channel_name = %s
            WHERE id = %s
            """
            cursor = self.db_connection.cursor()
            cursor.execute(query, (channel_id, channel_name, ticket_id))
            self.db_connection.commit()
            cursor.close()
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler bei update_ticket_channel: {e}")

    async def setup_categories(self, guild):
        """Erstellt die Kategorien, falls sie nicht existieren, und speichert deren IDs."""
        for name in self.categories.keys():
            category = discord.utils.get(guild.categories, id=self.categories.get(name))
            if not category:
                category = await guild.create_category(f"✉️ {name.capitalize()}")
                self.categories[name] = category.id
                print(f"[DEBUG] Kategorie erstellt: {name.capitalize()} (ID: {category.id})")
        self.save_category_ids()

    async def setup_ticket_channel(self, guild):
        """Erstellt oder aktualisiert den Ticket-Menü-Kanal."""
        menu_channel_id = self.config.get("menu_channel_id")
        menu_channel = discord.utils.get(guild.text_channels, id=menu_channel_id)

        # Kanal erstellen, falls er nicht existiert
        if not menu_channel:
            category_id = self.categories.get("menu")
            category = discord.utils.get(guild.categories, id=category_id)
            menu_channel = await guild.create_text_channel("ticket-channel", category=category)
            self.config["menu_channel_id"] = menu_channel.id
            self.save_config()

        # Prüfen, ob ein gültiges Embed existiert
        async for message in menu_channel.history(limit=50):
            if message.author == self.bot.user and message.embeds:
                print("[DEBUG] Vorhandenes Embed gefunden. Keine neuen Posts erforderlich.")
                return

        # Neues Embed posten
        embed = discord.Embed(
            title="🎫 Ticket-Support",
            description="Klicke auf den Button unten, um ein Ticket zu erstellen.",
            color=0x3498db,
        )
        view = TicketView(self.bot)
        await menu_channel.send(embed=embed, view=view)
        print("[DEBUG] Neues Ticket-Embed gepostet.")

    async def get_ticket_by_user(self, user_id):
        """Holt das Ticket eines Benutzers."""
        cursor = self.db_connection.cursor(dictionary=True)
        try:
            query = "SELECT * FROM tickets WHERE user_id = %s AND status = 'open'"
            cursor.execute(query, (user_id,))
            return cursor.fetchone()
        except Exception as e:
            print(f"[ERROR] Fehler bei get_ticket_by_user: {e}")
            return None
        finally:
            cursor.close()

    @app_commands.command(name="setup_tickets", description="Richtet die Ticket-Kategorien und das System ein.")
    @app_commands.default_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        """Richtet die Ticket-Kategorien und das Ticketsystem ein."""
        print("[DEBUG] setup_tickets Command wurde aufgerufen.")
        try:
            guild = interaction.guild
            await self.setup_categories(guild)
            await self.setup_ticket_channel(guild)

            await interaction.response.send_message("Das Ticketsystem wurde erfolgreich eingerichtet.", ephemeral=True)
        except Exception as e:
            print(f"[ERROR] Fehler bei setup_tickets: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)

class TicketActionView(View):
    def __init__(self, ticket_channel_id, bot):
        super().__init__(timeout=None)
        self.ticket_channel_id = ticket_channel_id
        self.bot = bot

    @discord.ui.button(label="🔒 Ticket schließen", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        """Schließt das Ticket."""
        channel = interaction.channel
        guild = interaction.guild

        tickets_cog = self.bot.get_cog("Tickets")
        if not tickets_cog:
            await interaction.response.send_message(
                "Das Ticketsystem ist nicht korrekt eingerichtet. Bitte kontaktiere einen Administrator.",
                ephemeral=True,
            )
            return
        if tickets_cog:
            tickets_cog.initialize_database()

        closed_category_id = tickets_cog.categories.get("geschlossen")
        closed_category = discord.utils.get(guild.categories, id=closed_category_id)
        if not closed_category:
            await interaction.response.send_message(
                "Die Kategorie ✉️ Ticket-Geschlossen existiert nicht. Bitte kontaktiere einen Administrator.",
                ephemeral=True,
            )
            return

        await channel.edit(category=closed_category)
        await channel.send("Dieses Ticket wurde geschlossen.")

        # Status in der Datenbank aktualisieren
        await tickets_cog.update_ticket_status(channel.id, "closed")
        await interaction.response.send_message("Das Ticket wurde geschlossen.", ephemeral=True)

class TicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🎫 Ticket erstellen", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        """Erstellt ein neues Ticket."""
        try:
            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild
            user = interaction.user
            tickets_cog = self.bot.get_cog("Tickets")
            print("[DEBUG] Interaktion gestartet: Ticket erstellen")

            if not tickets_cog:
                await interaction.followup.send("Das Ticketsystem ist nicht korrekt eingerichtet.", ephemeral=True)
                return

            erstellte_category_id = tickets_cog.categories.get("erstellte")
            erstellte_category = discord.utils.get(guild.categories, id=erstellte_category_id)
            if not erstellte_category:
                await interaction.followup.send(
                    "Die Kategorie für erstellte Tickets existiert nicht. Bitte kontaktiere einen Administrator.",
                    ephemeral=True
                )
                return

            existing_ticket = await tickets_cog.get_ticket_by_user(user.id)
            if existing_ticket:
                print(f"[DEBUG] Bestehendes Ticket gefunden: {existing_ticket}")
                await interaction.followup.send(
                    f"Du hast bereits ein Ticket: {existing_ticket.get('channel_name', 'Unbekannt')}.",
                    ephemeral=True
                )
                return

            # Ticket-Kanal erstellen
            try:
                ticket_channel = await guild.create_text_channel(
                    name=f"ticket-{user.name.lower()}",
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    },
                    category=erstellte_category,
                )
                print(f"[DEBUG] Ticket-Kanal erstellt: {ticket_channel.name}")
            except discord.Forbidden:
                await interaction.followup.send("Der Bot hat keine Berechtigung, Kanäle zu erstellen.", ephemeral=True)
                return
            except Exception as e:
                print(f"[ERROR] Fehler bei der Erstellung des Tickets: {e}")
                await interaction.followup.send(
                    "Ein Fehler ist aufgetreten. Bitte versuche es später erneut.",
                    ephemeral=True
                )
                return

            # Ticket-Details in der Datenbank speichern
            ticket_id = tickets_cog.create_ticket(user.id, 0, "", "Initiale Nachricht")
            if not ticket_id:
                await interaction.followup.send("Fehler beim Erstellen des Tickets. Bitte versuche es erneut.",
                                                ephemeral=True)
                return

            ticket_channel_name = f"ticket-{str(ticket_id).zfill(3)}"  # Z. B. ticket-001
            ticket_channel = await guild.create_text_channel(
                name=ticket_channel_name,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                },
                category=erstellte_category,
            )
            tickets_cog.update_ticket_channel(ticket_id, ticket_channel.id, ticket_channel_name)

        except Exception as e:
            print(f"[ERROR] Fehler bei der Verarbeitung der Interaktion: {e}")
            await interaction.followup.send("Ein Fehler ist aufgetreten. Bitte versuche es später erneut.",
                                            ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
