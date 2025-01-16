import discord
from discord.ext import commands
import mysql.connector
import json
import os


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
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
        except mysql.connector.Error as e:
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

    def load_category_ids(self):
        """Lädt gespeicherte Kategorien-IDs aus der Konfiguration."""
        for category_name in self.categories.keys():
            self.categories[category_name] = self.config.get(f"{category_name}_id")

    def save_category_ids(self):
        """Speichert die Kategorien-IDs in der Konfiguration."""
        for name, category_id in self.categories.items():
            if category_id:
                self.config[f"{name}_id"] = category_id
        self.save_config()

    def save_config(self):
        """Speichert die Konfigurationsdatei."""
        config_path = os.path.join(os.path.dirname(__file__), "../config.json")
        with open(config_path, "w") as file:
            json.dump(self.config, file, indent=4)

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

    @commands.command(name="setup_ticket", description="Richtet das Ticketsystem ein.")
    async def setup_ticket(self, interaction: discord.Interaction):
        """Richtet das Ticketsystem ein."""
        guild = interaction.guild
        categories_created = []
        categories_existing = []

        try:
            cursor = self.db_connection.cursor(dictionary=True)

            # Kategorien erstellen oder prüfen
            for name, _ in self.categories.items():
                query = "SELECT category_id FROM ticket_categories WHERE name = %s AND guild_id = %s"
                cursor.execute(query, (name, guild.id))
                category_data = cursor.fetchone()

                if not category_data:
                    # Kategorie erstellen
                    category = await guild.create_category(f"✉️ {name.capitalize()}")
                    categories_created.append(f"✉️ {name.capitalize()}")

                    # In der Datenbank speichern
                    query = "INSERT INTO ticket_categories (name, guild_id, category_id) VALUES (%s, %s, %s)"
                    cursor.execute(query, (name, guild.id, category.id))
                    self.db_connection.commit()
                    self.categories[name] = category.id
                    print(f"[DEBUG] Kategorie erstellt: {name.capitalize()} (ID: {category.id})")
                else:
                    # Kategorie existiert
                    categories_existing.append(f"✉️ {name.capitalize()}")
                    self.categories[name] = category_data["category_id"]

            # Menü-Channel erstellen oder prüfen
            query = "SELECT channel_id FROM ticket_menu WHERE guild_id = %s"
            cursor.execute(query, (guild.id,))
            menu_data = cursor.fetchone()

            if not menu_data:
                # Menü-Channel erstellen
                menu_category_id = self.categories.get("menu")
                menu_category = discord.utils.get(guild.categories, id=menu_category_id)

                if not menu_category:
                    await interaction.response.send_message(
                        "Fehler: Kategorie für Menü nicht gefunden. Kategorien müssen zuerst erstellt werden.",
                        ephemeral=True,
                    )
                    return

                # Erstelle den Channel in der Kategorie
                menu_channel = await guild.create_text_channel("ticket-menu", category=menu_category)

                # In der Datenbank speichern
                query = "INSERT INTO ticket_menu (guild_id, channel_id) VALUES (%s, %s)"
                cursor.execute(query, (guild.id, menu_channel.id))
                self.db_connection.commit()
                print(f"[DEBUG] Textkanal 'ticket-menu' erstellt (ID: {menu_channel.id}).")
            else:
                # Menü-Channel existiert
                menu_channel = discord.utils.get(guild.text_channels, id=menu_data["channel_id"])
                if not menu_channel:
                    # Wenn der Kanal in der Datenbank existiert, aber auf dem Server fehlt, neu erstellen
                    menu_category_id = self.categories.get("menu")
                    menu_category = discord.utils.get(guild.categories, id=menu_category_id)

                    menu_channel = await guild.create_text_channel("ticket-menu", category=menu_category)

                    # Datenbank aktualisieren
                    query = "UPDATE ticket_menu SET channel_id = %s WHERE guild_id = %s"
                    cursor.execute(query, (menu_channel.id, guild.id))
                    self.db_connection.commit()
                    print(f"[DEBUG] Textkanal 'ticket-menu' wurde neu erstellt (ID: {menu_channel.id}).")

            # Überprüfen, ob ein gültiges Embed existiert
            async for message in menu_channel.history(limit=50):
                if message.author == self.bot.user and message.embeds:
                    embed = message.embeds[0]
                    embed.title = "🎫 Ticket-Support"
                    embed.description = (
                        "Klicke auf den Button unten, um ein Ticket zu erstellen. "
                        "Missbrauch wird mit Ausschluss geahndet!"
                    )
                    embed.color = discord.Color.blue()
                    await message.edit(embed=embed, view=TicketView(self.bot))
                    print("[DEBUG] Vorhandenes Embed aktualisiert.")
                    await interaction.response.send_message(
                        "Das Ticketsystem wurde eingerichtet.",
                        ephemeral=True,
                    )
                    return

            # Neues Embed erstellen
            embed = discord.Embed(
                title="🎫 Ticket-Support",
                description="Klicke auf den Button unten, um ein Ticket zu erstellen. "
                            "Missbrauch wird mit Ausschluss geahndet!",
                color=discord.Color.blue(),
            )
            view = TicketView(self.bot)
            await menu_channel.send(embed=embed, view=view)
            print("[DEBUG] Neues Embed gepostet.")

            await interaction.response.send_message(
                f"Kategorien: {', '.join(categories_existing) if categories_existing else 'Keine'} existieren bereits.\n"
                f"Kategorien: {', '.join(categories_created) if categories_created else 'Keine'} wurden erstellt.\n"
                "Das Ticketsystem wurde erfolgreich eingerichtet.",
                ephemeral=True,
            )

        except Exception as e:
            print(f"[ERROR] Fehler bei setup_ticket: {e}")
            await interaction.response.send_message("❌ Ein Fehler ist aufgetreten.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
