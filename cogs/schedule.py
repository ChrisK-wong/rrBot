import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View
from datetime import datetime
from RadicalBowler import guild_id, channel_id


def embed(event, timestamp, attendance, color=0x22f7a5):
    embed = discord.Embed(title=f"{event} ⬦ "
                                f"{timestamp.strftime('%a %b %d' + suffix(timestamp.day) + ', %Y · %I:%M %p PT').replace(' 0', ' ')}",
                          description="", color=color)
    emojis = {"Can": "✅", "Can Sub": "❕", "Not Sure": "❔", "Can't": "❌", "Dropped": "❌"}
    for a in attendance:
        if len(attendance[a]) > 0:
            str_a = '\n'.join(attendance[a]).strip('\n')
            embed.add_field(name=f"{emojis[a]} {a} ({len(attendance[a])})", value=str_a, inline=False)
    return embed

def suffix(day):
    sfx = ""
    if 4 <= day <= 20 or 24 <= day <= 30:
        sfx = "th"
    else:
        sfx = ["st", "nd", "rd"][day % 10 - 1]
    return sfx


class Bs(Button):
    async def callback(self, interaction):
        if any(role.name == "Fans" for role in interaction.user.roles):
            await interaction.response.send_message("You do not have the permission!", ephemeral=True)
            return

        if interaction.message.embeds:
            emb = interaction.message.embeds[0].to_dict()

            title = emb['title'].split(" ⬦ ")
            d_t = title[1].split(",")
            d_t[1] = d_t[1].rstrip(" PT")
            timestamp = datetime.strptime(f"{d_t[0][:-2]} {d_t[1]}", "%a %b %d %Y · %I:%M %p")
            event = title[0]
            attendance = {"Can": [], "Can Sub": [], "Not Sure": [], "Can't": [], "Dropped": []}

            if 'fields' in emb:
                for field in emb['fields']:
                    attendance[field['name'][:-4].split(' ', 1)[1]] = field['value'].split('\n')
            dropped = False
            for a in attendance:
                if a != self.label and interaction.user.name in attendance[a]:
                    attendance[a].remove(interaction.user.name)
                    if self.label == "Can't":
                        dropped = True
            if dropped:
                attendance["Dropped"].append(interaction.user.name)
            else:
                if interaction.user.name not in attendance[self.label]:
                    attendance[self.label].append(interaction.user.name)

        await interaction.response.edit_message(embed=embed(event, timestamp, attendance))


class ButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Bs(label="Can", style=discord.ButtonStyle.green, emoji="✅"))
        self.add_item(Bs(label="Can Sub", style=discord.ButtonStyle.gray, emoji="❕"))
        self.add_item(Bs(label="Not Sure", style=discord.ButtonStyle.gray, emoji="❔"))
        self.add_item(Bs(label="Can't", style=discord.ButtonStyle.red, emoji="✖️"))


class Schedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.events = []

    @commands.Cog.listener()
    async def on_ready(self):
        c = await self.bot.fetch_channel(channel_id)
        async for m in c.history(limit=100):
            if m.author.id == self.bot.user.id:
                if m.embeds:
                    emb = m.embeds[0].to_dict()
                    if emb['color'] == 0xe15b62:
                        continue
                self.events.append(m.id)
                await m.edit(view=ButtonView())
        self.time.start()

    @tasks.loop(minutes=10)
    async def time(self):
        try:
            cur_time = timestamp = datetime.now()
            c = await self.bot.fetch_channel(channel_id)
            for event in self.events:
                m = await c.fetch_message(event)
                if m.embeds:
                    emb = m.embeds[0].to_dict()
                    try:
                        title = emb['title'].split(" ⬦ ")
                        d_t = title[1].split(",")
                        d_t[1] = d_t[1].rstrip(" PT")
                        timestamp = datetime.strptime(f"{d_t[0][:-2]} {d_t[1]}", "%a %b %d %Y · %I:%M %p")
                    except (ValueError, IndexError) as e:
                        emb['color'] = 0xe15b62
                        await m.edit(embed=discord.Embed.from_dict(emb), view=None)
                    if timestamp <= cur_time:
                        emb['color'] = 0xe15b62
                        await m.edit(embed=discord.Embed.from_dict(emb), view=None)
                        self.events.remove(event)
                else:
                    emb['color'] = 0xe15b62
                    await m.edit(embed=discord.Embed.from_dict(emb), view=None)
                    self.events.remove(event)
        except Exception as e:
            if isinstance(e, discord.errors.NotFound):
                print('error')
                self.events.remove(event)
            pass


    @app_commands.command(name='schedule',
                          description="Schedule an event!")
    @app_commands.describe(event="Event name")
    @app_commands.describe(date="Date format - ex:(3/12)")
    @app_commands.describe(time="12 hour format (PT) - ex:(3:30pm)")
    @app_commands.describe(message="Message/mentions - ex:(Please respond @Manager)")
    @app_commands.checks.has_any_role("Bot Manager", "Leaders", "Manager")
    async def schedule(self,
                       interaction: discord.Interaction,
                       event: str,
                       date: str,
                       time: str,
                       message: str) -> None:
        try:
            m_d = datetime.strptime(date, "%m/%d")
            cur_time = datetime.now()
            m_d = m_d.replace(year=cur_time.year)
        except ValueError:
            await interaction.response.send_message("Date format is incorrect", ephemeral=True)
            return
        try:
            t = datetime.strptime(time, "%I:%M%p").time()
        except ValueError:
            await interaction.response.send_message("Time format is incorrect", ephemeral=True)
            return
        timestamp = datetime.combine(m_d, t)
        if timestamp < cur_time:
            timestamp = timestamp.replace(year=cur_time.year + 1)
        view = ButtonView()
        attendance = {
            "Can": [],
            "Can Sub": [],
            "Not Sure": [],
            "Can't": []
        }
        await interaction.response.send_message(
            message,
            embed=embed(event, timestamp, attendance), view=view, ephemeral=False,
            allowed_mentions=discord.AllowedMentions(users=True, everyone=True, roles=True))
        s = await interaction.original_message()
        self.events.append(s.id)

    @schedule.error
    async def schedule_error(self,
                            interaction: discord.Interaction,
                            error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message("You do not have the permission!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(
        Schedule(bot),
        guilds=[discord.Object(id=guild_id)]
    )

