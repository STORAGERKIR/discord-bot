# 🤖 STORAGER Discord Bot

<div align="center">

### A powerful multi-level **Discord bot** built with `discord.py`, featuring:
🧠 Whitelist management • 🎮 Mini-games • 💬 DM utilities • 🔨 Moderation tools • 📢 Announcements  
and more — all with stylish embed responses and owner-only command protection.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Discord.py](https://img.shields.io/badge/discord.py-2.4.0-blueviolet?logo=discord)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Online-success)

</div>

---

## 🌟 Features

✅ **Multi-Level Whitelist System**
- `goon` — grants access to basic & moderator commands  
- `god` — full control, same power as the server owner  

✅ **Stylish Embed Responses**
- Every bot reply uses Discord embeds with color-coded visuals

✅ **Owner-Only Tools**
- Secure `!god`, `!mute`, `!poll`, `!announce`, and more

✅ **Mini-Game**
- Play the **💣 Bomb Grid Game (3x3)** with `!game`

✅ **Servers Command**
- View and select from known server setups with `!servers`

✅ **DM Utilities**
- Send direct messages to users or announce to channels
- `!opendm <username> <message>` — DM any user (even outside the server!)

✅ **Whitelist File Integration**
- Automatically managed `whitelist.txt` in the same folder as the bot

✅ **Smart Command Access**
- Non-whitelisted users get private “**ssshhh 🤫**” replies instead of errors

---

## 🧠 Command List (Updated)

<details>
<summary>📜 Click to expand command list</summary>

| Command | Access | Description |
|----------|--------|-------------|
| `!hello` | everyone | Greet the bot |
| `!secret` | everyone | DM a secret message |
| `!demote` | everyone | Remove all your roles |
| `!poll <question>` | owner | Create a poll |
| `!kick @user` | kick perms | Kick a member |
| `!ban @user` | ban perms | Ban a member |
| `!rps <rock/paper/scissors>` | everyone | Play Rock-Paper-Scissors |
| `!servers` | owner | View server info (Florian, Jacob, or PC Bureel) |
| `!god @user <msg>` | owner | Give all roles & DM |
| `!mute @user` | owner | Timeout a member |
| `!github` | everyone | Show GitHub link |
| `!commands` | everyone | Show this list |
| `!announce #channel <msg>` | owner | Send an embedded announcement |
| `!opendm <username> <msg>` | owner/god | DM any user by name |
| `!whitelist <user>` | owner/god | Add user to whitelist |
| `!unwhitelist <user>` | owner/god | Remove from whitelist |
| `!whitelistcheck` | owner/god | List whitelisted users |
| `!game` | owner/god | Play the 3x3 Bomb Game 💣 |

</details>

---

## ⚙️ Installation

### 1️⃣ Clone this repository
```bash
git clone https://github.com/STORAGERKIR/discord-bot.git
cd discord-bot
