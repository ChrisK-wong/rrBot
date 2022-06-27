import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True

# pip install -U git+https://github.com/Rapptz/discord.py

guild_id = # GUILD ID
channel_id = # CHANNEL ID

class RadicalBot(commands.Bot):
    def __init__(self, app_id):
        super().__init__(command_prefix=';',
                         intents=discord.Intents.all(),
                         application_id=app_id)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.user} has connected to Discord!")

    async def setup_hook(self):
        await self.load_extension("cogs.schedule")
        await bot.tree.sync(guild=discord.Object(id=guild_id))


if __name__ == "__main__":
    bot = RadicalBot(# BOT ID)
    bot.run(# BOT TOKEN)

