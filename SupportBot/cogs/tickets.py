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
        except Error as e:
            print(f"❌ Fehler bei der MySQL-Verbindung: {e}")
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
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(query)
            self.db_connection.commit()
            print("✅ Tabelle 'tickets_new' erfolgreich initialisiert.")
        except mysql.connector.Error as e:
            print(f"❌ Fehler bei der Initialisierung der Tabelle: {e}")

    def create_ticket(self, user_id, category_id):
        """Erstellt ein neues Ticket in der Datenbank."""
        try:
            query = "INSERT INTO tickets_new (user_id, category_id) VALUES (%s, %s)"
            cursor = self.db_connection.cursor()
            cursor.execute(query, (user_id, category_id))
            self.db_connection.commit()
            return cursor.lastrowid
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler bei create_ticket: {e}")
            return None

    def update_ticket(self, ticket_id, **kwargs):
        """Aktualisiert ein Ticket in der Datenbank."""
        try:
            updates = ", ".join([f"{key} = %s" for key in kwargs.keys()])
            query = f"UPDATE tickets_new SET {updates} WHERE id = %s"
            params = list(kwargs.values()) + [ticket_id]

            cursor = self.db_connection.cursor()
            cursor.execute(query, params)
            self.db_connection.commit()
            print(f"[DEBUG] Ticket {ticket_id} aktualisiert: {kwargs}")
        except mysql.connector.Error as e:
            print(f"[ERROR] Fehler bei update_ticket: {e}")

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

        erstellte_category_id = tickets_cog.categories.get("erstellte")
        erstellte_category = discord.utils.get(guild.categories, id=erstellte_category_id)
        if not erstellte_category:
            await interaction.response.send_message("Kategorie für Tickets nicht gefunden.", ephemeral=True)
            return

        ticket_id = tickets_cog.create_ticket(user.id, erstellte_category.id)
        if not ticket_id:
            await interaction.response.send_message("Fehler beim Erstellen des Tickets.", ephemeral=True)
            return

        channel_name = f"ticket-{str(ticket_id).zfill(3)}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        channel = await guild.create_text_channel(name=channel_name, category=erstellte_category, overwrites=overwrites)
        tickets_cog.update_ticket(ticket_id, channel_id=channel.id)

        await interaction.response.send_message(f"Ticket erstellt: {channel.mention}", ephemeral=True)

    # Schaltfläche: Ticket schließen
    @discord.ui.button(label="🔒 Ticket schließen", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        """Schließt das Ticket und verschiebt es in die geschlossene Kategorie."""
        tickets_cog = self.bot.get_cog("Tickets")
        if not tickets_cog:
            await interaction.response.send_message("Fehler: Ticketsystem nicht geladen.", ephemeral=True)
            return

        channel = interaction.channel
        guild = interaction.guild

        closed_category_id = tickets_cog.categories.get("geschlossen")
        closed_category = discord.utils.get(guild.categories, id=closed_category_id)
        if not closed_category:
            await interaction.response.send_message("Kategorie für geschlossene Tickets nicht gefunden.",
                                                    ephemeral=True)
            return

        await channel.edit(category=closed_category)
        tickets_cog.update_ticket(ticket_id=channel.id, status="closed")
        await interaction.response.send_message("Das Ticket wurde geschlossen.", ephemeral=True)

    # Schaltfläche: Ticket beanspruchen
    @discord.ui.button(label="📥 Ticket beanspruchen", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        """Markiert ein Ticket als beansprucht."""
        tickets_cog = self.bot.get_cog("Tickets")
        if not tickets_cog:
            await interaction.response.send_message("Fehler: Ticketsystem nicht geladen.", ephemeral=True)
            return

        channel = interaction.channel
        user = interaction.user

        claimed_category_id = tickets_cog.categories.get("uebernommen")
        claimed_category = discord.utils.get(channel.guild.categories, id=claimed_category_id)
        if not claimed_category:
            await interaction.response.send_message("Kategorie für beanspruchte Tickets nicht gefunden.",
                                                    ephemeral=True)
            return

        await channel.edit(category=claimed_category)
        tickets_cog.update_ticket(ticket_id=channel.id, status="claimed")
        await interaction.response.send_message(f"Das Ticket wurde von {user.mention} beansprucht.", ephemeral=True)

    # Schaltfläche: Ticket freigeben
    @discord.ui.button(label="🔄 Ticket freigeben", style=discord.ButtonStyle.green, custom_id="release_ticket")
    async def release_ticket(self, interaction: discord.Interaction, button: Button):
        """Markiert ein Ticket als freigegeben."""
        tickets_cog = self.bot.get_cog("Tickets")
        if not tickets_cog:
            await interaction.response.send_message("Fehler: Ticketsystem nicht geladen.", ephemeral=True)
            return

        channel = interaction.channel

        released_category_id = tickets_cog.categories.get("freigegeben")
        released_category = discord.utils.get(channel.guild.categories, id=released_category_id)
        if not released_category:
            await interaction.response.send_message("Kategorie für freigegebene Tickets nicht gefunden.",
                                                    ephemeral=True)
            return

        await channel.edit(category=released_category)
        tickets_cog.update_ticket(ticket_id=channel.id, status="open")
        await interaction.response.send_message("Das Ticket wurde freigegeben.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
