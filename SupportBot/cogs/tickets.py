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
        self.load_category_ids()  # Ruft die neue Methode auf

    def load_category_ids(self):
        """Lädt gespeicherte Kategorien-IDs aus der Konfiguration."""
        for category_name in self.categories.keys():
            self.categories[category_name] = self.config.get(f"{category_name}_id")

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

    def save_category_ids(self):
        """Speichert die Kategorien-IDs in der Konfiguration."""
        for name, category_id in self.categories.items():
            if category_id:
                self.config[f"{name}_id"] = category_id
        self.save_config()


class TicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @app_commands.command(name="setup_ticket", description="Richtet das Ticketsystem ein.")
    async def setup_ticket(self, interaction: discord.Interaction):
        """Richtet das Ticketsystem ein."""
        guild = interaction.guild
        categories_created = []
        categories_existing = []

        try:
            cursor = self.db_connection.cursor(dictionary=True)

            # Kategorien erstellen oder prüfen
            for name, _ in self.categories.items():
                query = "SELECT id, category_id FROM ticket_categories WHERE name = %s AND guild_id = %s"
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
                    print(f"[DEBUG] Kategorie erstellt: {name.capitalize()} (ID: {category.id})")
                else:
                    # Kategorie existiert
                    categories_existing.append(f"✉️ {name.capitalize()}")
                    self.categories[name] = category_data["category_id"]

            # Textkanal für das Ticket-Menü erstellen oder prüfen
            query = "SELECT channel_id FROM ticket_menu WHERE guild_id = %s"
            cursor.execute(query, (guild.id,))
            menu_data = cursor.fetchone()

            if not menu_data:
                # Menükanal erstellen
                menu_category_id = self.categories.get("menu")
                menu_category = discord.utils.get(guild.categories, id=menu_category_id)
                if not menu_category:
                    await interaction.response.send_message(
                        "Fehler: Kategorie für Menü nicht gefunden. Kategorien müssen zuerst erstellt werden.",
                        ephemeral=True,
                    )
                    return

                menu_channel = await guild.create_text_channel("ticket-menu", category=menu_category)

                # In der Datenbank speichern
                query = "INSERT INTO ticket_menu (guild_id, channel_id) VALUES (%s, %s)"
                cursor.execute(query, (guild.id, menu_channel.id))
                self.db_connection.commit()
                print(f"[DEBUG] Textkanal 'ticket-menu' erstellt (ID: {menu_channel.id}).")
            else:
                menu_channel = discord.utils.get(guild.text_channels, id=menu_data["channel_id"])
                if not menu_channel:
                    # Kanal existiert nicht mehr, neu erstellen
                    menu_category_id = self.categories.get("menu")
                    menu_category = discord.utils.get(guild.categories, id=menu_category_id)
                    menu_channel = await guild.create_text_channel("ticket-menu", category=menu_category)

                    # Datenbank aktualisieren
                    query = "UPDATE ticket_menu SET channel_id = %s WHERE guild_id = %s"
                    cursor.execute(query, (menu_channel.id, guild.id))
                    self.db_connection.commit()
                    print(f"[DEBUG] Textkanal 'ticket-menu' wurde neu erstellt (ID: {menu_channel.id}).")
                else:
                    print(f"[DEBUG] Textkanal 'ticket-menu' existiert bereits (ID: {menu_channel.id}).")

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
                        f"Kategorien: {', '.join(categories_existing) if categories_existing else 'Keine'} existieren bereits.\n"
                        f"Kategorien: {', '.join(categories_created) if categories_created else 'Keine'} wurden erstellt.\n"
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
