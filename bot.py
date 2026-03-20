import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

sticky_data = {}
timer_tasks = {}

# ---------- FILE SYSTEM ---------- #

def load_data():
    global sticky_data
    try:
        with open("sticky.json", "r") as f:
            sticky_data = json.load(f)
    except:
        sticky_data = {}

def save_data():
    with open("sticky.json", "w") as f:
        json.dump(sticky_data, f, indent=4)

# ---------- BUTTONS ---------- #

class StickyView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = str(channel_id)

    @discord.ui.button(label="✏️ Edit", style=discord.ButtonStyle.primary)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Use /sticky change to edit.", ephemeral=True)

    @discord.ui.button(label="🗑 Remove", style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.channel_id in sticky_data:
            del sticky_data[self.channel_id]
            save_data()
            await interaction.response.send_message("Sticky removed.", ephemeral=True)
        else:
            await interaction.response.send_message("No sticky found.", ephemeral=True)

# ---------- TIMER ---------- #

async def sticky_timer(channel):
    channel_id = str(channel.id)

    while True:
        await asyncio.sleep(60)

        data = sticky_data.get(channel_id)
        if not data:
            return

        now = asyncio.get_event_loop().time()

        if now - data["last_message_time"] >= 60:
            try:
                if data.get("message_id"):
                    old_msg = await channel.fetch_message(data["message_id"])
                    await old_msg.delete()
            except:
                pass

            embed = discord.Embed(
                title="📌 Sticky Message",
                description=data["text"],
                color=discord.Color.blue()
            )

            view = StickyView(channel.id)

            msg = await channel.send(embed=embed, view=view)
            sticky_data[channel_id]["message_id"] = msg.id
            save_data()

        else:
            continue

# ---------- EVENTS ---------- #

@bot.event
async def on_ready():
    load_data()
    await tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    channel_id = str(message.channel.id)

    if channel_id in sticky_data:
        sticky_data[channel_id]["last_message_time"] = asyncio.get_event_loop().time()

        if channel_id in timer_tasks:
            timer_tasks[channel_id].cancel()

        timer_tasks[channel_id] = bot.loop.create_task(sticky_timer(message.channel))

# ---------- SLASH COMMANDS ---------- #

@tree.command(name="sticky_set", description="Set a sticky message")
@app_commands.describe(message="Your sticky message")
async def sticky_set(interaction: discord.Interaction, message: str):
    channel_id = str(interaction.channel.id)

    sticky_data[channel_id] = {
        "text": message,
        "message_id": None,
        "last_message_time": asyncio.get_event_loop().time()
    }

    save_data()

    # 🔥 START TIMER RIGHT AWAY
    if channel_id in timer_tasks:
        timer_tasks[channel_id].cancel()

    timer_tasks[channel_id] = bot.loop.create_task(sticky_timer(interaction.channel))

    await interaction.response.send_message(
        "✅ Sticky set! Will post after 1 minute of inactivity.",
        ephemeral=True
    )


@tree.command(name="sticky_change", description="Change sticky message")
@app_commands.describe(message="New sticky message")
async def sticky_change(interaction: discord.Interaction, message: str):
    channel_id = str(interaction.channel.id)

    if channel_id not in sticky_data:
        await interaction.response.send_message("❌ No sticky set.", ephemeral=True)
        return

    sticky_data[channel_id]["text"] = message
    save_data()

    await interaction.response.send_message("✏️ Sticky updated.", ephemeral=True)


@tree.command(name="sticky_remove", description="Remove sticky message")
async def sticky_remove(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)

    if channel_id not in sticky_data:
        await interaction.response.send_message("❌ No sticky found.", ephemeral=True)
        return

    try:
        if sticky_data[channel_id]["message_id"]:
            msg = await interaction.channel.fetch_message(sticky_data[channel_id]["message_id"])
            await msg.delete()
    except:
        pass

    del sticky_data[channel_id]
    save_data()

    await interaction.response.send_message("🗑 Sticky removed.", ephemeral=True)


@tree.command(name="sticky_info", description="Check current sticky message")
async def sticky_info(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)

    if channel_id not in sticky_data:
        await interaction.response.send_message("❌ No sticky set.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"📌 Current sticky:\n{sticky_data[channel_id]['text']}",
        ephemeral=True
    )


bot.run(TOKEN)
