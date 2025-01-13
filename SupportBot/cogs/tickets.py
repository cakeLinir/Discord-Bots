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
            message TEXT,
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

        if not menu_channel:
            category_id = self.categories.get("menu")
            category = discord.utils.get(guild.categories, id=category_id)
            menu_channel = await guild.create_text_channel("ticket-channel", category=category)
            self.config["menu_channel_id"] = menu_channel.id
            self.save_config()

        async for message in menu_channel.history(limit=50):
            if message.author == self.bot.user and message.embeds:
                print("[DEBUG] Vorhandenes Embed gefunden. Keine neuen Posts erforderlich.")
                return

        embed = discord.Embed(
            title="🎫 Ticket-Support",
            description="Beim Verwenden des Buttons wird ein neues Ticket erstellt. Bitte missbrauchen Sie das System nicht.",
            color=0x3498db,
        )
        view = TicketView(self.bot)
        await menu_channel.send(embed=embed, view=view)
        print("[DEBUG] Neues Ticket-Embed gepostet.")

    @app_commands.command(name="setup_tickets", description="Richtet die Ticket-Kategorien und das System ein.")
    @app_commands.default_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        """Richtet die Ticket-Kategorien und das Ticketsystem ein."""
        try:
            guild = interaction.guild
            await self.setup_categories(guild)
            await self.setup_ticket_channel(guild)
            await interaction.response.send_message("Das Ticketsystem wurde erfolgreich eingerichtet.", ephemeral=True)
        except Exception as e:
            print(f"[ERROR] Fehler bei setup_tickets: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)


class TicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🎫 Ticket erstellen", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        """Erstellt ein neues Ticket."""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user
        tickets_cog = self.bot.get_cog("Tickets")

        if not tickets_cog:
            await interaction.followup.send("Das Ticketsystem ist nicht korrekt eingerichtet.", ephemeral=True)
            return

        try:
            erstellte_category_id = tickets_cog.categories.get("erstellte")
            erstellte_category = discord.utils.get(guild.categories, id=erstellte_category_id)
            if not erstellte_category:
                await interaction.followup.send(
                    "Die Kategorie für erstellte Tickets existiert nicht. Bitte kontaktieren Sie einen Administrator.",
                    ephemeral=True,
                )
                return

            ticket_id = tickets_cog.create_ticket(user.id, 0, "")
            if not ticket_id:
                raise Exception("Ticket konnte nicht in der Datenbank erstellt werden.")

            ticket_channel_name = f"ticket-{str(ticket_id).zfill(3)}"
            ticket_channel = await guild.create_text_channel(
                name=ticket_channel_name,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                },
                category=erstellte_category,
            )
            tickets_cog.update_ticket_channel(ticket_id, ticket_channel.id, ticket_channel_name)
            await interaction.followup.send(f"Ticket erstellt: {ticket_channel.mention}", ephemeral=True)
        except Exception as e:
            print(f"[ERROR] Fehler bei der Erstellung des Tickets: {e}")
            await interaction.followup.send("Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.",
                                            ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
