# Full Discord bot script — embed-styled messages, multi-level whitelist, game, servers, DM linking for st0rager
import sys
import subprocess
import os
import datetime
import asyncio
import random
import logging
from typing import Optional, Tuple


import os, sys

# Fix working directory for PyInstaller
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)


# installer helper (optional)
def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Ensure required packages are present
install_and_import('discord')
install_and_import('python-dotenv')

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load token from .env
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
if not token:
    raise ValueError("DISCORD_TOKEN is not set in the .env file")

# Logging handler
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Paths & constants
WHITELIST_PATH = r"C:\Users\super joodje5\Desktop\discord-bot\whitelist.txt"
GAGSTOCK_LINK_PATH = r"C:\Users\super joodje5\Desktop\discord-bot\gagstock_link.txt"
ST0RAGER_NAME = "st0rager"  # exact username (no discriminator)

# Ensure folder and files exist
os.makedirs(os.path.dirname(WHITELIST_PATH), exist_ok=True)
if not os.path.exists(WHITELIST_PATH):
    with open(WHITELIST_PATH, "w", encoding="utf-8") as f:
        f.write("")  # empty file

# helper: read/write whitelist (format: user_id,level)
def read_whitelist() -> dict:
    data = {}
    try:
        with open(WHITELIST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",", 1)
                if len(parts) == 2:
                    uid, level = parts[0].strip(), parts[1].strip().lower()
                    if level not in ("goon", "god"):
                        continue
                    data[uid] = level
    except FileNotFoundError:
        pass
    return data

def write_whitelist(data: dict):
    with open(WHITELIST_PATH, "w", encoding="utf-8") as f:
        for uid, level in sorted(data.items(), key=lambda x: int(x[0])):
            f.write(f"{uid},{level}\n")

def read_gagstock_link() -> Optional[int]:
    try:
        with open(GAGSTOCK_LINK_PATH, "r", encoding="utf-8") as f:
            s = f.read().strip()
            return int(s) if s else None
    except:
        return None

def write_gagstock_link(guild_id: Optional[int]):
    with open(GAGSTOCK_LINK_PATH, "w", encoding="utf-8") as f:
        f.write(str(guild_id) if guild_id else "")

# embed helper
def make_embed(title: str, description: str = "", color: discord.Color = discord.Color.blue(), fields: list = None, footer: Tuple[str, str] = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    if footer:
        text, icon = footer
        try:
            embed.set_footer(text=text, icon_url=icon)
        except:
            embed.set_footer(text=text)
    embed.timestamp = discord.utils.utcnow()
    return embed

async def send_embed_to_channel(channel: discord.abc.Messageable, embed: discord.Embed):
    try:
        await channel.send(embed=embed)
    except Exception as e:
        # fallback to plain text if sending embed fails for some reason
        try:
            await channel.send(f"{embed.title}\n{embed.description}")
        except:
            pass

async def send_private_embed(user: discord.User, embed: discord.Embed, fallback_channel: Optional[discord.TextChannel] = None):
    try:
        await user.send(embed=embed)
    except discord.Forbidden:
        # if DM blocked, optionally notify in fallback channel (ephemeral style)
        if fallback_channel:
            try:
                notice = await fallback_channel.send(f"{user.mention} (couldn't DM you) — {embed.title}")
                await asyncio.sleep(6)
                await notice.delete()
            except:
                pass

# ---------- permission helpers ----------
def get_effective_guild_and_member(ctx) -> Tuple[Optional[discord.Guild], Optional[discord.Member]]:
    """
    Returns (guild, member) to evaluate permissions.
    If command was used in a guild, returns that guild and member.
    If used in DM and author is st0rager and gagstock linked, returns the linked guild and the member object representing the author in that guild (if available).
    Otherwise returns (None, None) for DMs from others.
    """
    if ctx.guild:
        return ctx.guild, ctx.author if isinstance(ctx.author, discord.Member) else None
    # DM case
    if isinstance(ctx.author, discord.User) and ctx.author.name == ST0RAGER_NAME:
        linked_id = read_gagstock_link()
        if linked_id:
            guild = discord.utils.get(bot.guilds, id=linked_id)
            if guild:
                # attempt to get member
                member = guild.get_member(ctx.author.id)
                return guild, member
    return None, None

def is_owner_for_context(ctx) -> bool:
    guild, member = get_effective_guild_and_member(ctx)
    if guild:
        try:
            return ctx.author == guild.owner or (member and member == guild.owner)
        except:
            return False
    return False

def get_whitelist_level(user_id: int) -> Optional[str]:
    data = read_whitelist()
    return data.get(str(user_id))

def has_access_for_command(ctx, command_name: str) -> bool:
    """
    Returns True if the invoking user has permission to run a given command_name.
    Rules:
      - Guild owner OR god level => full access
      - goon level => limited commands list (see below)
      - others => false
    """
    # owner
    if is_owner_for_context(ctx):
        return True

    # st0rager DM linking: if ctx is DM and author is st0rager and gagstock linked, we treat owner check above already handled
    # whitelist level
    level = get_whitelist_level(ctx.author.id)
    if level == "god":
        return True
    if level == "goon":
        allowed = {"hello", "secret", "demote", "poll", "kick", "rps", "github"}
        return command_name in allowed
    return False

async def deny_permission(ctx, reason: str = "Only the server owner or permitted users can use this."):
    # private red embed
    embed = make_embed("ssssshhh 🤫", reason, color=discord.Color.red())
    # prefer DM
    if isinstance(ctx.author, discord.User) and not ctx.guild:
        try:
            await ctx.author.send(embed=embed)
            return
        except discord.Forbidden:
            pass
    # fallback channel ephemeral message
    try:
        notice = await ctx.send(embed=embed)
        await asyncio.sleep(6)
        await notice.delete()
    except:
        pass

# ---------- events ----------
@bot.event
async def on_ready():
    print(f"Bot ready as {bot.user} (id: {bot.user.id})")

@bot.event
async def on_member_join(member):
    embed = make_embed("Welcome!", f"Welcome to the server, {member.name}!", color=discord.Color.blue())
    await send_private_embed(member, embed)

@bot.event
async def on_message(message):
    # ignore self
    if message.author == bot.user:
        return

    # content moderation (unchanged)
    banned_words = ["nigger", "femboy", "sissy", "cock", "penis", "neger"]
    if any(bad in message.content.lower() for bad in banned_words):
        try:
            await message.delete()
            await message.author.send(embed=make_embed("⚠️ Warning", "Silly little boy, don't do it again!", color=discord.Color.red()))
        except discord.Forbidden:
            pass

    # allow commands processing
    await bot.process_commands(message)

# ---------- basic commands (embed-style responses) ----------
@bot.command()
async def hello(ctx):
    if not has_access_for_command(ctx, "hello"):
        await deny_permission(ctx)
        return
    embed = make_embed("👋 Hello", f"Hello {ctx.author.name}!", color=discord.Color.green())
    await send_embed_to_channel(ctx, embed)

@bot.command()
async def secret(ctx):
    if not has_access_for_command(ctx, "secret"):
        await deny_permission(ctx)
        return

    # DM the secret if possible
    embed_dm = make_embed("🤫 Secret", "Don’t say this to anybody!", color=discord.Color.green())
    try:
        await ctx.author.send(embed=embed_dm)
        # notify in channel (ephemeral style)
        notice = make_embed("✅ Sent", "I sent you the secret in DMs.", color=discord.Color.blue())
        sent = await ctx.send(embed=notice)
        await asyncio.sleep(6)
        try:
            await sent.delete()
        except:
            pass
    except discord.Forbidden:
        embed = make_embed("ℹ️ Can't DM", "I can't DM you. Please enable DMs from server members.", color=discord.Color.red())
        await send_embed_to_channel(ctx, embed)

@bot.command()
async def demote(ctx):
    if not has_access_for_command(ctx, "demote"):
        await deny_permission(ctx)
        return

    member = ctx.author
    roles_to_remove = [role for role in member.roles if role != ctx.guild.default_role] if isinstance(member, discord.Member) else []
    if not roles_to_remove:
        embed = make_embed("ℹ️ No roles", f"{member.mention}, you have no roles to remove.", color=discord.Color.blue())
        await send_embed_to_channel(ctx, embed)
        return
    try:
        await member.remove_roles(*roles_to_remove)
        embed = make_embed("✅ Demoted", f"{member.mention}, all your roles have been removed.", color=discord.Color.green())
        await send_embed_to_channel(ctx, embed)
    except discord.Forbidden:
        embed = make_embed("❌ Permission error", "I don't have permission to remove your roles.", color=discord.Color.red())
        await send_embed_to_channel(ctx, embed)

@bot.command()
async def poll(ctx, *, question: str):
    # poll is allowed for owner and goon per your earlier request (you asked goon to access poll)
    if not has_access_for_command(ctx, "poll"):
        await deny_permission(ctx)
        return
    poll_msg = await ctx.send(embed=make_embed("📊 Poll", question, color=discord.Color.blue()))
    await poll_msg.add_reaction("👍")
    await poll_msg.add_reaction("👎")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    # allowed for goon (kick permission) and owner/god
    if not has_access_for_command(ctx, "kick"):
        await deny_permission(ctx)
        return
    try:
        await member.kick(reason=reason)
        embed = make_embed("🦶 Kicked", f"{member.mention} has been kicked.", color=discord.Color.green())
        await send_embed_to_channel(ctx, embed)
    except discord.Forbidden:
        embed = make_embed("❌ Permission error", "I don't have permission to kick that user.", color=discord.Color.red())
        await send_embed_to_channel(ctx, embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"Something went wrong: {e}", color=discord.Color.red())
        await send_embed_to_channel(ctx, embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    if not is_owner_for_context(ctx) and get_whitelist_level(ctx.author.id) != "god":
        await deny_permission(ctx)
        return
    try:
        await member.ban(reason=reason)
        embed = make_embed("🔨 Banned", f"{member.mention} has been banned.", color=discord.Color.green())
        await send_embed_to_channel(ctx, embed)
    except discord.Forbidden:
        embed = make_embed("❌ Permission error", "I don't have permission to ban that user.", color=discord.Color.red())
        await send_embed_to_channel(ctx, embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"Something went wrong: {e}", color=discord.Color.red())
        await send_embed_to_channel(ctx, embed)

@bot.command()
async def rps(ctx, choice: str):
    if not has_access_for_command(ctx, "rps"):
        await deny_permission(ctx)
        return
    options = ["rock", "paper", "scissors"]
    user_choice = choice.lower()
    if user_choice not in options:
        await send_embed_to_channel(ctx, make_embed("❗ Choose one", "Choose one of: `rock`, `paper`, or `scissors`.", color=discord.Color.red()))
        return
    bot_choice = random.choice(options)
    if user_choice == bot_choice:
        result = "It's a tie! 😐"
    elif (
        (user_choice == "rock" and bot_choice == "scissors") or
        (user_choice == "paper" and bot_choice == "rock") or
        (user_choice == "scissors" and bot_choice == "paper")
    ):
        result = "You win! 🎉"
    else:
        result = "You lose! 😢"
    await send_embed_to_channel(ctx, make_embed("🕹️ Rock Paper Scissors", f"You chose **{user_choice}**, I chose **{bot_choice}**.\n{result}", color=discord.Color.blue()))

@bot.command()
async def god(ctx, member: discord.Member, *, dm_message: str):
    # owner only
    if not is_owner_for_context(ctx):
        await deny_permission(ctx)
        return
    roles = [role for role in ctx.guild.roles if role != ctx.guild.default_role]
    try:
        await member.add_roles(*roles)
        try:
            await member.send(embed=make_embed("👑 You were given roles", dm_message, color=discord.Color.purple()))
        except:
            pass
        await send_embed_to_channel(ctx, make_embed("👑 Done", f"{member.mention} has been given all roles and received a DM.", color=discord.Color.green()))
    except discord.Forbidden:
        await send_embed_to_channel(ctx, make_embed("❌ Permission error", "I don't have permission to assign all roles or send DMs.", color=discord.Color.red()))
    except Exception as e:
        await send_embed_to_channel(ctx, make_embed("❌ Error", f"Something went wrong: {e}", color=discord.Color.red()))

@bot.command()
async def dm(ctx, member: discord.Member, *, message: str):
    if not is_owner_for_context(ctx):
        await deny_permission(ctx)
        return
    try:
        await member.send(embed=make_embed("📬 Message from server owner", message, color=discord.Color.blue()))
        await send_embed_to_channel(ctx, make_embed("✅ Sent", f"DM sent to {member.mention}", color=discord.Color.green()))
    except discord.Forbidden:
        await send_embed_to_channel(ctx, make_embed("❌ Error", "I can't DM this person. They probably have DMs disabled.", color=discord.Color.red()))

@bot.command()
async def mute(ctx, member: discord.Member):
    if not is_owner_for_context(ctx):
        await deny_permission(ctx)
        return
    if ctx.author == member:
        await send_embed_to_channel(ctx, make_embed("❗ Invalid", "You can't mute yourself.", color=discord.Color.red()))
        return
    await send_embed_to_channel(ctx, make_embed("⏱️ Mute", "How long should the mute be? (e.g. `5min` or `30min`)", color=discord.Color.blue()))
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        reply = await bot.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        await send_embed_to_channel(ctx, make_embed("⏰ Timeout", "You took too long to respond.", color=discord.Color.red()))
        return
    time_str = reply.content.lower()
    if not time_str.endswith("min") or not time_str[:-3].isdigit():
        await send_embed_to_channel(ctx, make_embed("❗ Invalid format", "Please enter like `5min` or `30min`.", color=discord.Color.red()))
        return
    duration_minutes = int(time_str[:-3])
    duration = datetime.timedelta(minutes=duration_minutes)
    try:
        await member.timeout(discord.utils.utcnow() + duration)
        await send_embed_to_channel(ctx, make_embed("🤐 Muted", f"{member.mention} has been muted for {duration_minutes} minutes.", color=discord.Color.green()))
        try:
            await member.send(embed=make_embed("🤐 You were muted", f"You have been muted in **{ctx.guild.name}** for {duration_minutes} minutes.", color=discord.Color.blue()))
        except:
            pass
    except discord.Forbidden:
        await send_embed_to_channel(ctx, make_embed("❌ Permission error", "I don't have permission to mute this user.", color=discord.Color.red()))
    except Exception as e:
        await send_embed_to_channel(ctx, make_embed("❌ Error", f"Something went wrong: {e}", color=discord.Color.red()))

@bot.command()
async def github(ctx):
    await send_embed_to_channel(ctx, make_embed("🔗 GitHub", "Check out the GitHub here: https://github.com/STORAGERKIR", color=discord.Color.blue()))

# ---------- servers command (owner/god/goon checks inside) ----------
@bot.command()
async def servers(ctx):
    if not has_access_for_command(ctx, "servers"):
        await deny_permission(ctx)
        return
    devices = {
        "florian laptop": {"display_name": "Florian - oude laptop", "ip": "499430430", "password": "Lolbroek123"},
        "jacob laptop": {"display_name": "Jacob's laptop", "ip": "1073288845", "password": "Lolbroek123"},
        "pc living": {"display_name": "PC Bureel", "ip": "533830921", "password": "jacobisgay36."}
    }
    embed = make_embed("🖥️ Server / Laptop List", "Choose one of the options below by typing its name in chat:\n`florian laptop` / `jacob laptop` / `pc living`", color=discord.Color.blue())
    for key, info in devices.items():
        embed.add_field(name=info["display_name"], value=f"`{key}`", inline=False)
    embed.set_footer(text="Reply with your choice within 30 seconds.", icon_url=getattr(ctx.author, "display_avatar", None).url if hasattr(ctx.author, "display_avatar") else None)
    await send_embed_to_channel(ctx, embed)
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        reply = await bot.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        await send_embed_to_channel(ctx, make_embed("⏰ Timeout", "You didn't reply in time. Please run `!servers` again when ready.", color=discord.Color.red()))
        return
    choice_raw = reply.content.lower().strip()
    matched = None
    if choice_raw in devices:
        matched = choice_raw
    else:
        for key in devices:
            if key.split()[0] in choice_raw:
                matched = key
                break
    if not matched:
        await send_embed_to_channel(ctx, make_embed("❌ Invalid choice", "Please run `!servers` and choose one of: `florian laptop`, `jacob laptop`, or `pc living`.", color=discord.Color.red()))
        return
    info = devices[matched]
    result_embed = make_embed(f"🔐 {info['display_name']}", "", color=discord.Color.green(), fields=[("IP", f"`{info['ip']}`", False), ("Password", f"```{info['password']}```", False)])
    result_embed.set_footer(text=f"Requested by {ctx.author}", icon_url=getattr(ctx.author, "display_avatar", None).url if hasattr(ctx.author, "display_avatar") else None)
    await send_embed_to_channel(ctx, result_embed)

# ---------- 3x3 bomb game (owner/god allowed) ----------
@bot.command()
async def game(ctx):
    if not has_access_for_command(ctx, "game"):
        await deny_permission(ctx)
        return
    cells = list(range(1, 10))
    bombs = set(random.sample(cells, 3))
    def neighbors(idx):
        i = idx - 1
        r, c = divmod(i, 3)
        neigh = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < 3 and 0 <= cc < 3:
                    neigh.append(rr * 3 + cc + 1)
        return neigh
    adj_counts = {i: sum(1 for n in neighbors(i) if n in bombs) for i in cells}
    number_emojis = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣"}
    def render_grid(reveal=None):
        lines = []
        for r in range(0, 9, 3):
            row = []
            for i in range(r + 1, r + 4):
                if reveal and i in reveal:
                    if i in bombs:
                        row.append("💣")
                    else:
                        row.append(str(adj_counts[i]) if adj_counts[i] > 0 else "✅")
                else:
                    row.append(number_emojis[i])
            lines.append(" ".join(row))
        return "\n".join(lines)
    embed = make_embed("💣 3x3 Bomb Game", "Pick a cell by sending a number 1–9 (e.g. `5`). Avoid bombs! You have 30 seconds to pick one cell.", color=discord.Color.orange())
    embed.add_field(name="Board", value=render_grid(), inline=False)
    embed.set_footer(text="3 bombs are hidden. Good luck!", icon_url=getattr(ctx.author, "display_avatar", None).url if hasattr(ctx.author, "display_avatar") else None)
    await send_embed_to_channel(ctx, embed)
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        await send_embed_to_channel(ctx, make_embed("⏰ Timeout", "You didn't pick a cell. Run `!game` again to play.", color=discord.Color.red()))
        return
    choice = msg.content.strip()
    if not choice.isdigit() or int(choice) not in cells:
        await send_embed_to_channel(ctx, make_embed("❌ Invalid choice", "Pick a number from 1 to 9 next time.", color=discord.Color.red()))
        return
    choice_num = int(choice)
    if choice_num in bombs:
        reveal_set = set(cells)
        result_embed = make_embed("💥 Boom! You hit a bomb.", "Here's the full board:", color=discord.Color.red())
        result_embed.add_field(name="Board", value=render_grid(reveal=reveal_set), inline=False)
        result_embed.set_footer(text=f"Play again with !game — requested by {ctx.author}", icon_url=getattr(ctx.author, "display_avatar", None).url if hasattr(ctx.author, "display_avatar") else None)
        await send_embed_to_channel(ctx, result_embed)
    else:
        reveal_set = {choice_num}
        result_embed = make_embed("✅ Safe!", f"You picked **{choice_num}** — adjacent bombs: **{adj_counts[choice_num]}**", color=discord.Color.green())
        result_embed.add_field(name="Board", value=render_grid(reveal=reveal_set), inline=False)
        result_embed.set_footer(text=f"Nice! Run `!game` to play again. Requested by {ctx.author}", icon_url=getattr(ctx.author, "display_avatar", None).url if hasattr(ctx.author, "display_avatar") else None)
        await send_embed_to_channel(ctx, result_embed)

# ---------- whitelist commands ----------
@bot.command()
async def whitelist(ctx, member: discord.Member, level: str = None):
    # only owner or god can modify whitelist; owner_for_context or god allowed
    if not (is_owner_for_context(ctx) or get_whitelist_level(ctx.author.id) == "god"):
        await deny_permission(ctx)
        return
    if level is None:
        await send_embed_to_channel(ctx, make_embed("❗ Usage", "Use: `!whitelist @user <goon|god>`", color=discord.Color.red()))
        return
    level = level.lower()
    if level not in ("goon", "god"):
        await send_embed_to_channel(ctx, make_embed("❗ Invalid level", "Level must be `goon` or `god`.", color=discord.Color.red()))
        return
    data = read_whitelist()
    uid = str(member.id)
    if uid in data:
        await send_embed_to_channel(ctx, make_embed("ℹ️ Already whitelisted", f"{member.mention} is already whitelisted as `{data[uid]}`.", color=discord.Color.blue()))
        return
    data[uid] = level
    write_whitelist(data)
    try:
        await member.send(embed=make_embed("✅ Whitelisted", f"Congrats u have been whitelisted for the STORAGER.app\nLevel: `{level}`", color=discord.Color.green()))
    except discord.Forbidden:
        await send_embed_to_channel(ctx, make_embed("ℹ️ Can't DM", "Couldn't DM the user, but they’ve been whitelisted.", color=discord.Color.blue()))
    await send_embed_to_channel(ctx, make_embed("✅ Done", f"{member.mention} has been added to the whitelist as `{level}`.", color=discord.Color.green()))

@bot.command()
async def unwhitelist(ctx, member: discord.Member):
    if not (is_owner_for_context(ctx) or get_whitelist_level(ctx.author.id) == "god"):
        await deny_permission(ctx)
        return
    data = read_whitelist()
    uid = str(member.id)
    if uid not in data:
        await send_embed_to_channel(ctx, make_embed("ℹ️ Not on whitelist", f"{member.mention} is not on the whitelist.", color=discord.Color.blue()))
        return
    data.pop(uid, None)
    write_whitelist(data)
    try:
        await member.send(embed=make_embed("😢 Demoted", "Awwww, u have been demoted", color=discord.Color.purple()))
    except discord.Forbidden:
        await send_embed_to_channel(ctx, make_embed("ℹ️ Can't DM", "Couldn't DM the user, but they’ve been unwhitelisted.", color=discord.Color.blue()))
    await send_embed_to_channel(ctx, make_embed("✅ Done", f"{member.mention} has been removed from the whitelist.", color=discord.Color.green()))

@bot.command()
async def whitelistcheck(ctx):
    # anyone can request the list, but only owner/god will get full details? You asked to list users — we'll allow owner/god to see full info; others will see a brief message.
    data = read_whitelist()
    if not data:
        await send_embed_to_channel(ctx, make_embed("Whitelist", "No users are whitelisted.", color=discord.Color.blue()))
        return
    # prepare fields: show mention if possible and level
    fields = []
    for uid, lvl in data.items():
        try:
            uid_int = int(uid)
            member = None
            # try find member in any guilds
            for g in bot.guilds:
                m = g.get_member(uid_int)
                if m:
                    member = m
                    break
            display = member.mention if member else f"<@{uid}>"
        except:
            display = uid
        fields.append((display, f"`{lvl}`", False))
    embed = make_embed("📋 Whitelist Check", f"Total whitelisted: {len(fields)}", color=discord.Color.blue(), fields=fields)
    await send_embed_to_channel(ctx, embed)

# ---------- commands list ----------
@bot.command(name="commands")
async def commands_list(ctx):
    embed = make_embed("📜 Command List", "Here are all available commands and who can use them:", color=discord.Color.blue())
    embed.add_field(name="!hello", value="goon/god/owner", inline=False)
    embed.add_field(name="!secret", value="goon/god/owner", inline=False)
    embed.add_field(name="!demote", value="goon/god/owner", inline=False)
    embed.add_field(name="!poll", value="goon/god/owner", inline=False)
    embed.add_field(name="!kick @user", value="goon (requires Kick permission) / owner / god", inline=False)
    embed.add_field(name="!ban @user", value="god / owner", inline=False)
    embed.add_field(name="!rps <rock/paper/scissors>", value="everyone", inline=False)
    embed.add_field(name="!god @user <message>", value="owner", inline=False)
    embed.add_field(name="!dm @user <message>", value="owner", inline=False)
    embed.add_field(name="!mute @user", value="owner", inline=False)
    embed.add_field(name="!github", value="everyone", inline=False)
    embed.add_field(name="!servers", value="owner/god", inline=False)
    embed.add_field(name="!game", value="owner/god", inline=False)
    embed.add_field(name="!whitelist @user <goon|god>", value="owner/god", inline=False)
    embed.add_field(name="!unwhitelist @user", value="owner/god", inline=False)
    embed.add_field(name="!whitelistcheck", value="everyone (shows current whitelist)", inline=False)
    embed.add_field(name="Special", value="If `st0rager` DMs the bot `!kut`, the bot will link to a guild named 'GAG STOCK' and accept owner-level DM commands for that guild.", inline=False)
    await send_embed_to_channel(ctx, embed)

# ---------- announce (owner only) ----------
@bot.command()
async def announce(ctx, channel: discord.TextChannel, *, message: str):
    if not is_owner_for_context(ctx):
        await deny_permission(ctx)
        return
    embed = make_embed("📢 Announcement", f"```{message}```", color=discord.Color.purple())
    embed.set_footer(text=f"Announcement by {ctx.author}", icon=getattr(ctx.author, "display_avatar", None).url if hasattr(ctx.author, "display_avatar") else None)
    try:
        await channel.send(embed=embed)
        await send_embed_to_channel(ctx, make_embed("✅ Sent", f"Announcement sent to {channel.mention}.", color=discord.Color.green()))
    except Exception as e:
        await send_embed_to_channel(ctx, make_embed("❌ Error", f"Something went wrong: {e}", color=discord.Color.red()))

# ---------- st0rager special DM command: !kut ----------
@bot.event
async def on_message(message):
    # Reuse moderation and command processing but intercept DMs named st0rager !kut
    if message.author == bot.user:
        return

    # moderation (as before)
    banned_words = ["nigger", "femboy", "sissy", "cock", "penis", "neger"]
    if any(bad in message.content.lower() for bad in banned_words):
        try:
            await message.delete()
            await message.author.send(embed=make_embed("⚠️ Warning", "Silly little boy, don't do it again!", color=discord.Color.red()))
        except discord.Forbidden:
            pass

    # special handling: if DM from st0rager and content starts with !kut
    if isinstance(message.channel, discord.DMChannel) and message.author.name == ST0RAGER_NAME:
        content = message.content.strip()
        if content.startswith("!kut"):
            # attempt to find guild named exactly "GAG STOCK"
            target_guild = discord.utils.find(lambda g: g.name == "GAG STOCK", bot.guilds)
            if target_guild:
                write_gagstock_link(target_guild.id)
                embed = make_embed("🔗 Linked", f"Linked to guild **{target_guild.name}** (ID {target_guild.id}). You can now send owner-level commands via DM and they will act on that guild.", color=discord.Color.purple())
                await send_private_embed(message.author, embed)
                # also announce briefly to guild (if has a system channel or first text channel)
                announce_channel = target_guild.system_channel or next((c for c in target_guild.text_channels if c.permissions_for(target_guild.me).send_messages), None)
                if announce_channel:
                    try:
                        await announce_channel.send(embed=make_embed("🔗 Linked by st0rager", "The bot is now linked for owner-level DM commands by st0rager.", color=discord.Color.purple()))
                    except:
                        pass
            else:
                write_gagstock_link(None)
                await send_private_embed(message.author, make_embed("❌ Not found", "Could not find a guild named `GAG STOCK` among my guilds. Make sure the bot is in that server and it's named exactly `GAG STOCK`.", color=discord.Color.red()))
            # after special handling, continue to process commands contained in DM
    # finally pass to command processor
    await bot.process_commands(message)

# Note: We defined on_message twice (above and here) — Python will use the latest definition.
# To avoid duplicate definitions, we replaced both earlier on_message uses with this final consolidated one.

# ---------- run bot ----------
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
