import discord
from discord.ext import commands
from discord.ui import Button, View


class TicketView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🎫 Ticket erstellen", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket_button(self, interaction: discord.Interaction, button: Button):
        """Erstellt ein neues Ticket."""
        tickets_cog = self.bot.get_cog("Tickets")
        if not tickets_cog:
            await interaction.response.send_message("Fehler: Ticketsystem ist nicht geladen.", ephemeral=True)
            return

        guild = interaction.guild
        user = interaction.user

        # Kategorie für erstellte Tickets abrufen
        erstellte_category_id = tickets_cog.categories.get("erstellte")
        erstellte_category = discord.utils.get(guild.categories, id=erstellte_category_id)
        if not erstellte_category:
            await interaction.response.send_message("Kategorie für Tickets nicht gefunden.", ephemeral=True)
            return

        # Neues Ticket erstellen
        ticket_id = tickets_cog.create_ticket(user.id, erstellte_category.id)
        if not ticket_id:
            await interaction.response.send_message("Fehler beim Erstellen des Tickets.", ephemeral=True)
            return

        # Kanalname und Berechtigungen definieren
        channel_name = f"ticket-{str(ticket_id).zfill(3)}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        channel = await guild.create_text_channel(name=channel_name, category=erstellte_category, overwrites=overwrites)

        # Kanal-ID in der Datenbank speichern
        tickets_cog.update_ticket(ticket_id=ticket_id, channel_id=channel.id)

        # Antwort an den Benutzer
        await interaction.response.send_message(f"Ticket erstellt: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="🔒 Ticket schließen", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket_button(self, interaction: discord.Interaction, button: Button):
        """Schließt ein Ticket und verschiebt es in die geschlossene Kategorie."""
        tickets_cog = self.bot.get_cog("Tickets")
        if not tickets_cog:
            await interaction.response.send_message("Fehler: Ticketsystem ist nicht geladen.", ephemeral=True)
            return

        channel = interaction.channel
        guild = interaction.guild

        # Kategorie für geschlossene Tickets abrufen
        closed_category_id = tickets_cog.categories.get("geschlossen")
        closed_category = discord.utils.get(guild.categories, id=closed_category_id)
        if not closed_category:
            await interaction.response.send_message("Kategorie für geschlossene Tickets nicht gefunden.", ephemeral=True)
            return

        # Ticket verschieben und Status aktualisieren
        await channel.edit(category=closed_category)
        tickets_cog.update_ticket(ticket_id=channel.id, status="closed")
        await interaction.response.send_message("Das Ticket wurde geschlossen.", ephemeral=True)

    @discord.ui.button(label="📥 Ticket beanspruchen", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket_button(self, interaction: discord.Interaction, button: Button):
        """Beansprucht ein Ticket und verschiebt es in die übernommene Kategorie."""
        tickets_cog = self.bot.get_cog("Tickets")
        if not tickets_cog:
            await interaction.response.send_message("Fehler: Ticketsystem ist nicht geladen.", ephemeral=True)
            return

        channel = interaction.channel
        guild = interaction.guild

        # Kategorie für übernommene Tickets abrufen
        claimed_category_id = tickets_cog.categories.get("uebernommen")
        claimed_category = discord.utils.get(guild.categories, id=claimed_category_id)
        if not claimed_category:
            await interaction.response.send_message("Kategorie für übernommene Tickets nicht gefunden.", ephemeral=True)
            return

        # Ticket verschieben und Status aktualisieren
        await channel.edit(category=claimed_category)
        tickets_cog.update_ticket(ticket_id=channel.id, status="claimed")
        await interaction.response.send_message(f"Das Ticket wurde von {interaction.user.mention} beansprucht.", ephemeral=True)

    @discord.ui.button(label="🔄 Ticket freigeben", style=discord.ButtonStyle.green, custom_id="release_ticket")
    async def release_ticket_button(self, interaction: discord.Interaction, button: Button):
        """Gibt ein Ticket frei und verschiebt es in die freigegebene Kategorie."""
        tickets_cog = self.bot.get_cog("Tickets")
        if not tickets_cog:
            await interaction.response.send_message("Fehler: Ticketsystem ist nicht geladen.", ephemeral=True)
            return

        channel = interaction.channel
        guild = interaction.guild

        # Kategorie für freigegebene Tickets abrufen
        released_category_id = tickets_cog.categories.get("freigegeben")
        released_category = discord.utils.get(guild.categories, id=released_category_id)
        if not released_category:
            await interaction.response.send_message("Kategorie für freigegebene Tickets nicht gefunden.", ephemeral=True)
            return

        # Ticket verschieben und Status aktualisieren
        await channel.edit(category=released_category)
        tickets_cog.update_ticket(ticket_id=channel.id, status="open")
        await interaction.response.send_message("Das Ticket wurde freigegeben.", ephemeral=True)

class TicketViewCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Registriere die View global
        bot.add_view(TicketView(bot))

async def setup(bot: commands.Bot):
    await bot.add_cog(TicketViewCog(bot))
