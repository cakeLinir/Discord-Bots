import discord
from discord.ext import commands
from discord import app_commands
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Privacy(commands.Cog):
    """Cog für Datenschutz und Datenverwaltung."""

    def __init__(self, bot):
        self.bot = bot
        self.db_connection = bot.db_connection  # Zugriff auf die Datenbankverbindung

    @app_commands.command(name="privacy", description="Zeigt die Datenschutzrichtlinien des Bots.")
    async def privacy(self, interaction: discord.Interaction):
        """Zeigt die Datenschutzrichtlinien des Bots."""
        embed = discord.Embed(
            title="Datenschutzrichtlinien",
            description=(
                "Dieser Bot verarbeitet und speichert personenbezogene Daten gemäß der DSGVO.\n"
                "- **Gespeicherte Daten:**\n"
                "  - Discord-ID: Wird zur Identifikation von Nutzern verwendet.\n"
                "  - Clash of Clans-Spieler-Tags: Wird zur Verifizierung und Verwaltung von Clan-Mitgliedern genutzt.\n"
                "  - Verschlüsselte Clash of Clans API-Tokens: Falls angegeben, für automatisierte Anfragen an die API.\n\n"
                "- **Zweck der Datenverarbeitung:**\n"
                "  - Verifizierung und Zuweisung von Rollen basierend auf der Clan-Hierarchie.\n"
                "  - Automatische Überprüfung der Mitgliedschaft im Clan.\n"
                "  - Verwaltung und Organisation von Clan-Aktivitäten.\n\n"
                "- **Speicherfrist:**\n"
                "  - Daten werden nach dem Verlassen des Clans für **72 Stunden** gespeichert, um sicherzustellen, dass Benutzer die Möglichkeit haben, zurückzukehren.\n"
                "  - Nach Ablauf von 72 Stunden werden die Daten automatisch gelöscht.\n\n"
                "- **Datenlöschung:**\n"
                "  - Benutzer können ihre Daten jederzeit mit `/delete_data` löschen.\n"
                "  - **Konsequenzen beim Löschen der Daten:**\n"
                "    - Der Benutzer wird aus der Verifizierung entfernt.\n"
                "    - Zugewiesene Rollen werden entfernt.\n"
                "    - Der Benutzer verliert den Zugriff auf geschützte Clan-Kanäle.\n\n"
                "- **Datenexport:**\n"
                "  - Mit `/export_data` können Benutzer ihre gespeicherten Daten einsehen.\n\n"
                "Vielen Dank für die Verwendung dieses Bots!"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Dieser Bot entspricht der DSGVO.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="export_data", description="Exportiert deine gespeicherten Daten.")
    async def export_data(self, interaction: discord.Interaction):
        """Exportiert die gespeicherten Daten eines Benutzers."""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                "SELECT player_tag, role FROM users WHERE discord_id = %s",
                (interaction.user.id,)
            )
            result = cursor.fetchone()
            cursor.close()

            if result:
                player_tag, role = result
                await interaction.response.send_message(
                    f"**Deine gespeicherten Daten:**\n"
                    f"- **Discord-ID:** {interaction.user.id}\n"
                    f"- **Clash of Clans-Spieler-Tag:** {player_tag}\n"
                    f"- **Rolle:** {role}\n"
                    "\nHinweis: Diese Daten werden gemäß DSGVO gespeichert.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Es wurden keine Daten zu deiner ID gefunden.", ephemeral=True
                )
        except Exception as e:
            logger.error(f"Fehler beim Exportieren der Daten: {e}")
            await interaction.response.send_message(
                "Es ist ein Fehler beim Abrufen deiner Daten aufgetreten.", ephemeral=True
            )

    @app_commands.command(name="delete_data", description="Löscht deine gespeicherten Daten.")
    async def delete_data(self, interaction: discord.Interaction):
        """Löscht die gespeicherten Daten eines Benutzers und entfernt zugewiesene Rollen."""
        try:
            roles_to_remove_ids = [
                1326598627245953026,  # Beispiel: Leader
                1326598628927737986,  # Beispiel: coLeader
                1326598629833834497,  # Beispiel: Elder
                1326598631234736151  # Beispiel: Member
            ]
            removed_roles = []

            if interaction.guild is None:
                await interaction.response.send_message(
                    "Dieser Befehl kann nur auf einem Server ausgeführt werden.", ephemeral=True
                )
                return

            # Rollen entfernen
            for role_id in roles_to_remove_ids:
                discord_role = interaction.guild.get_role(role_id)
                if discord_role:
                    if discord_role in interaction.user.roles:
                        await interaction.user.remove_roles(discord_role)
                        removed_roles.append(discord_role.name)
                    else:
                        logger.info(f"Benutzer hat die Rolle {discord_role.name} nicht.")
                else:
                    logger.warning(f"Rolle mit ID {role_id} wurde nicht gefunden.")

            # Benutzer aus der Datenbank entfernen
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM users WHERE discord_id = %s", (interaction.user.id,))
            self.db_connection.commit()
            cursor.close()

            # Rückmeldung senden
            removed_roles_list = ", ".join(removed_roles) if removed_roles else "Keine Rollen entfernt."
            await interaction.response.send_message(
                f"Deine gespeicherten Daten wurden erfolgreich gelöscht.\n\n"
                f"**Entfernte Rollen:** {removed_roles_list}\n\n"
                f"**Konsequenzen der Datenlöschung:**\n"
                f"- Du hast keinen Zugriff auf geschützte Clan-Kanäle mehr.\n"
                f"- Du musst dich erneut verifizieren, um Zugriff zu erhalten.",
                ephemeral=True
            )

            logger.info(
                f"Benutzer {interaction.user.id} hat seine Daten und Rollen gelöscht. Entfernte Rollen: {removed_roles_list}")

        except Exception as e:
            logger.error(f"Fehler beim Löschen der Daten: {e}")
            await interaction.response.send_message(
                "Es ist ein Fehler beim Löschen deiner Daten aufgetreten.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Privacy(bot))
