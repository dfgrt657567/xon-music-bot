# 🎵 Discord Music Bot

Ek powerful aur modern **Discord Music Bot** jo YouTube links, search queries, queue management aur full playback control support karta hai.

---

## 🚀 Setup Guide (Kadam-dar-Kadam)

### 1. Requirements Install Karein
Sabse pehle terminal ya command prompt open karke dependencies install karein:

```bash
pip install -r requirements.txt
```

---

### 2. FFmpeg Install Karein (Zaruri)
Discord par audio stream karne ke liye **FFmpeg** hona zaruri hai:

- **Windows me (Fastest via Winget)**:
  ```powershell
  winget install Gyan.FFmpeg
  ```
- Ya fir [FFmpeg Official Website](https://ffmpeg.org/download.html) se download karke `ffmpeg.exe` ko PATH me add karein ya isi project folder me daal dein.

---

### 3. Discord Bot Token Banayein
1. [Discord Developer Portal](https://discord.com/developers/applications) par jaayein.
2. **"New Application"** par click karein aur bot ka naam rakhein.
3. Left menu me **"Bot"** tab par click karein.
4. **"Reset Token"** par click karke token copy karein.
5. Usi page par neeche scroll karein aur **"Privileged Gateway Intents"** ke andar ye 3 options enable karein:
   - ✅ **Presence Intent**
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent** (Ye sabse zaruri hai!)
6. **Save Changes** par click karein.

---

### 4. Bot ko apne Server me Invite Karein
1. Developer Portal me **"OAuth2"** -> **"URL Generator"** par click karein.
2. **SCOPES** me select karein:
   - `bot`
   - `applications.commands`
3. **BOT PERMISSIONS** me select karein:
   - `Send Messages`
   - `Embed Links`
   - `Connect`
   - `Speak`
   - `Use Voice Activity`
   *(Ya Administrator de sakte hain)*
4. Neeche generated URL ko copy karke browser me paste karein aur apne server me bot add karein.

---

### 5. Configuration (.env)
Project folder me `.env` file open karein aur apna token paste karein:

```env
DISCORD_TOKEN=apna_discord_bot_token_yahan_dalein
BOT_PREFIX=!
```

---

### 6. Bot Start Karein
Ab bot ko start karein:

```bash
python bot.py
```

---

## 🎶 Music Commands List

| Command | Alias | Description |
| :--- | :--- | :--- |
| `!play <song/URL>` | `!p` | YouTube link ya song name search karke play karega |
| `!pause` | | Running music ko pause karega |
| `!resume` | `!unpause` | Paused music ko wapas play karega |
| `!skip` | `!s` | Agle gaane par jump karega |
| `!stop` | | Music band karega aur queue khali karega |
| `!queue` | `!q` | Current song queue list dikhayega |
| `!nowplaying` | `!np` | Currently playing gaane ki details dikhayega |
| `!volume <0-100>` | `!vol` | Sound volume change karega |
| `!loop` | `!repeat` | Current gaana repeat mode par lagayega |
| `!clear` | | Up-next queue ko clear karega |
| `!join` | `!j` | Bot ko voice channel me bulayega |
| `!leave` | `!dc` | Bot ko voice channel se disconnect karega |
| `!musichelp` | `!mhelp` | Saare commands ki list embed me dikhayega |

---

## 📁 Project Structure

```
bot/
├── cogs/
│   └── music.py          # Music playback engine & commands
├── .env                  # Configuration (Bot Token & Prefix)
├── .env.example          # Sample env template
├── bot.py                # Main bot startup & event handler
├── requirements.txt      # Python libraries
└── README.md             # Guide & documentation
```
