import discord
import json
import os
from discord.ext import commands
from discord import app_commands

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = os.path.join(os.path.dirname(__file__), "../config.json")
        self.config = self.load_config()

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
    async def add_support_role(self, interaction: discord.Interaction, role_id: str):
        """Fügt eine Supportrolle hinzu."""
        if role_id not in self.config["support_roles"]:
            self.config["support_roles"].append(role_id)
            self.save_config()
            await interaction.response.send_message(f"Rolle mit ID {role_id} wurde als Supportrolle hinzugefügt.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Rolle mit ID {role_id} ist bereits eine Supportrolle.", ephemeral=True)
        await self.bot.tree.sync()

    @app_commands.command(name="remove_support_role", description="Entfernt eine Supportrolle.")
    @app_commands.describe(role_id="Die ID der zu entfernenden Rolle.")
    async def remove_support_role(self, interaction: discord.Interaction, role_id: str):
        """Entfernt eine Supportrolle."""
        if role_id in self.config["support_roles"]:
            self.config["support_roles"].remove(role_id)
            self.save_config()
            await interaction.response.send_message(f"Rolle mit ID {role_id} wurde entfernt.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Rolle mit ID {role_id} ist keine Supportrolle.", ephemeral=True)
        await self.bot.tree.sync()

    @app_commands.command(name="add_support_user", description="Fügt einen Benutzer als Supporter hinzu.")
    @app_commands.describe(user_id="Die ID des hinzuzufügenden Benutzers.")
    async def add_support_user(self, interaction: discord.Interaction, user_id: str):
        """Fügt einen Benutzer als Supporter hinzu."""
        if user_id not in self.config["support_users"]:
            self.config["support_users"].append(user_id)
            self.save_config()
            await interaction.response.send_message(f"Benutzer mit ID {user_id} wurde als Supporter hinzugefügt.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Benutzer mit ID {user_id} ist bereits ein Supporter.", ephemeral=True)
        await self.bot.tree.sync()

    @app_commands.command(name="remove_support_user", description="Entfernt einen Benutzer als Supporter.")
    @app_commands.describe(user_id="Die ID des zu entfernenden Benutzers.")
    async def remove_support_user(self, interaction: discord.Interaction, user_id: str):
        """Entfernt einen Benutzer als Supporter."""
        if user_id in self.config["support_users"]:
            self.config["support_users"].remove(user_id)
            self.save_config()
            await interaction.response.send_message(f"Benutzer mit ID {user_id} wurde entfernt.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Benutzer mit ID {user_id} ist kein Supporter.", ephemeral=True)
        await self.bot.tree.sync()

    @app_commands.command(name="set_support_channel", description="Legt den Kanal für Support-Threads fest.")
    @app_commands.describe(channel_id="Die ID des Support-Kanals.")
    async def set_support_channel(self, interaction: discord.Interaction, channel_id: str):
        """Legt den Kanal für Support-Threads fest."""
        self.config["support_channel_id"] = channel_id
        self.save_config()
        await interaction.response.send_message(f"Support-Kanal wurde auf ID {channel_id} gesetzt.", ephemeral=True)
        await self.bot.tree.sync()

    @app_commands.command(name="list_support_config", description="Listet die aktuelle Support-Konfiguration auf.")
    async def list_support_config(self, interaction: discord.Interaction):
        """Listet die aktuelle Support-Konfiguration auf."""
        support_roles = "\n".join(self.config["support_roles"]) or "Keine Rollen konfiguriert."
        support_users = "\n".join(self.config["support_users"]) or "Keine Benutzer konfiguriert."
        support_channel = self.config["support_channel_id"] or "Kein Kanal konfiguriert."

        embed = discord.Embed(
            title="Aktuelle Support-Konfiguration",
            color=0x3498db
        )
        embed.add_field(name="Support-Rollen", value=support_roles, inline=False)
        embed.add_field(name="Support-Benutzer", value=support_users, inline=False)
        embed.add_field(name="Support-Kanal", value=support_channel, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.bot.tree.sync()
        print(f"[DEBUG] Aktuelle Slash-Commands: {self.bot.tree.get_commands()}")


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
