import json
import os
import discord
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
            channel_id BIGINT,
            category_id BIGINT,
            status ENUM('open', 'claimed', 'closed') DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor = self.db_connection.cursor()
        cursor.execute(query)
        self.db_connection.commit()

    def load_category_ids(self):
        """Lädt gespeicherte Kategorien-IDs."""
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

    def create_ticket(self, user_id, category_id):
        """Erstellt ein neues Ticket in der Datenbank und gibt die Ticket-ID zurück."""
        try:
            query = "INSERT INTO tickets_new (user_id, category_id) VALUES (%s, %s)"
            cursor = self.db_connection.cursor()
            cursor.execute(query, (user_id, category_id))
            self.db_connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"[ERROR] Fehler bei create_ticket: {e}")
            return None

    def update_ticket(self, ticket_id, status=None, channel_id=None, category_id=None):
        """Aktualisiert den Status oder die Kanal-/Kategorieinformationen eines Tickets."""
        query = "UPDATE tickets_new SET "
        updates = []
        params = []

        if status:
            updates.append("status = %s")
            params.append(status)
        if channel_id:
            updates.append("channel_id = %s")
            params.append(channel_id)
        if category_id:
            updates.append("category_id = %s")
            params.append(category_id)

        query += ", ".join(updates) + " WHERE id = %s"
        params.append(ticket_id)

        try:
            cursor = self.db_connection.cursor()
            cursor.execute(query, tuple(params))
            self.db_connection.commit()
            print(f"[DEBUG] Ticket {ticket_id] aktualisiert: {updates}")
        except Error as e:
            print(f"[ERROR] Fehler bei update_ticket: {e}")

    async def setup_categories(self, guild):
        """Erstellt die Kategorien, falls sie nicht existieren, und speichert deren IDs."""
        for name in self.categories.keys():
            category = discord.utils.get(guild.categories, id=self.categories.get(name))
            if not category:
                category = await guild.create_category(f"✉️ {name.capitalize()}")
                self.categories[name] = category.id
                print(f"[DEBUG] Kategorie erstellt: {name.capitalize()} (ID: {category.id})")
        self.save_category_ids()

class TicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🎫 Ticket erstellen", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket_button(self, interaction: discord.Interaction, button: Button):
        """Erstellt ein neues Ticket."""
        tickets_cog = self.bot.get_cog("Tickets")
        if not tickets_cog:
            await interaction.response.send_message("Fehler: Ticketsystem nicht geladen.", ephemeral=True)
            return

        guild = interaction.guild
        user = interaction.user

        # Kategorie für erstellte Tickets abrufen
        erstellte_category_id = tickets_cog.categories.get("erstellte")
        erstellte_category = discord.utils.get(guild.categories, id=erstellte_category_id)
        if not erstellte_category:
            await interaction.response.send_message("Kategorie für Tickets nicht gefunden.", ephemeral=True)
            return

        # Ticket-ID erstellen
        ticket_id = tickets_cog.create_ticket(user.id, erstellte_category.id)
        if not ticket_id:
            await interaction.response.send_message("Fehler beim Erstellen des Tickets.", ephemeral=True)
            return

        # Kanal erstellen
        channel_name = f"ticket-{str(ticket_id).zfill(3)}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        channel = await guild.create_text_channel(name=channel_name, category=erstellte_category, overwrites=overwrites)

        # Kanal-ID aktualisieren
        tickets_cog.update_ticket(ticket_id, channel_id=channel.id)

        await interaction.response.send_message(f"Ticket erstellt: {channel.mention}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
