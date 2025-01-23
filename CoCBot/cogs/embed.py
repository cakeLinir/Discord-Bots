import discord
from discord.ext import commands
import logging
from discord import app_commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbedManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create_embed", description="Erstellt ein neues Embed über eine Eingabemaske.")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_embed(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Führt den Benutzer durch die Erstellung eines neuen Embeds."""
        await interaction.response.send_message("Beginnen wir mit dem Erstellen des Embeds. Antworten Sie auf die Fragen!", ephemeral=True)

        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel

        try:
            # Titel
            await interaction.followup.send("Was soll der Titel des Embeds sein?")
            title_msg = await self.bot.wait_for("message", check=check, timeout=120)
            title = title_msg.content

            # Beschreibung
            await interaction.followup.send("Was soll die Beschreibung des Embeds sein?")
            description_msg = await self.bot.wait_for("message", check=check, timeout=120)
            description = description_msg.content

            # Farbe
            await interaction.followup.send("Welche Farbe soll das Embed haben? (Hex-Code, z.B. #3498db)")
            color_msg = await self.bot.wait_for("message", check=check, timeout=120)
            color = int(color_msg.content.lstrip("#"), 16)

            # Felder hinzufügen
            fields = []
            while True:
                await interaction.followup.send("Möchten Sie ein Feld hinzufügen? (Ja/Nein)")
                add_field_msg = await self.bot.wait_for("message", check=check, timeout=120)
                if add_field_msg.content.lower() not in ["ja", "yes"]:
                    break

                await interaction.followup.send("Geben Sie den Namen des Feldes ein:")
                field_name_msg = await self.bot.wait_for("message", check=check, timeout=120)
                field_name = field_name_msg.content

                await interaction.followup.send("Geben Sie den Wert des Feldes ein:")
                field_value_msg = await self.bot.wait_for("message", check=check, timeout=120)
                field_value = field_value_msg.content

                fields.append({"name": field_name, "value": field_value, "inline": True})

            # Embed erstellen
            embed = discord.Embed(title=title, description=description, color=color)
            for field in fields:
                embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])

            # Nachricht senden
            message = await channel.send(embed=embed)

            await interaction.followup.send(f"Embed erfolgreich erstellt! [Nachricht ansehen](https://discord.com/channels/{interaction.guild.id}/{channel.id}/{message.id})")

        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Embeds: {e}")
            await interaction.followup.send("Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.", ephemeral=True)

    @app_commands.command(name="edit_embed", description="Bearbeitet ein vorhandenes Embed.")
    @app_commands.checks.has_permissions(administrator=True)
    async def edit_embed(self, interaction: discord.Interaction, channel: discord.TextChannel, message_id: int):
        """Führt den Benutzer durch das Bearbeiten eines vorhandenen Embeds."""
        await interaction.response.send_message("Beginnen wir mit dem Bearbeiten des Embeds. Antworten Sie auf die Fragen!", ephemeral=True)

        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel

        try:
            # Nachricht abrufen
            message = await channel.fetch_message(message_id)
            if not message.embeds:
                await interaction.followup.send("Die Nachricht enthält kein Embed. Abbruch.", ephemeral=True)
                return

            embed = message.embeds[0]

            # Titel bearbeiten
            await interaction.followup.send(f"Der aktuelle Titel ist: {embed.title}\nNeuer Titel? (Leer lassen, um unverändert zu lassen)")
            title_msg = await self.bot.wait_for("message", check=check, timeout=120)
            title = title_msg.content if title_msg.content else embed.title

            # Beschreibung bearbeiten
            await interaction.followup.send(f"Die aktuelle Beschreibung ist: {embed.description}\nNeue Beschreibung? (Leer lassen, um unverändert zu lassen)")
            description_msg = await self.bot.wait_for("message", check=check, timeout=120)
            description = description_msg.content if description_msg.content else embed.description

            # Farbe bearbeiten
            await interaction.followup.send(f"Die aktuelle Farbe ist: {embed.color}\nNeue Farbe? (Hex-Code, z.B. #3498db oder leer lassen)")
            color_msg = await self.bot.wait_for("message", check=check, timeout=120)
            color = int(color_msg.content.lstrip("#"), 16) if color_msg.content else embed.color

            # Aktualisiertes Embed erstellen
            new_embed = discord.Embed(title=title, description=description, color=color)
            for field in embed.fields:
                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)

            await message.edit(embed=new_embed)

            await interaction.followup.send(f"Embed erfolgreich bearbeitet! [Nachricht ansehen](https://discord.com/channels/{interaction.guild.id}/{channel.id}/{message.id})")

        except Exception as e:
            logger.error(f"Fehler beim Bearbeiten des Embeds: {e}")
            await interaction.followup.send("Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(EmbedManager(bot))
