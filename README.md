# Telegram Message Transfer Tool v2.7

A powerful, asynchronous Python script designed to transfer messages, photos, and videos between Telegram chats, channels, or forum topics. It supports bulk transfers via message ID ranges, handles media albums (grouped media) correctly, and can bypass forwarding restrictions by downloading and re-uploading content.

---

## 🚀 Features

* **Bulk Transfer:** Move large volumes of messages using a specified ID range (e.g., `1-5000`).
* **Media Support:** Handles Photos, Videos, and Text with granular toggles.
* **Album Awareness:** Correctly detects and maintains the structure of media groups (albums).
* **Topic Support:** Transfer content to and from specific forum topics using the `chat_id:topic_id` format.
* **Bypass Restrictions:** Automatically switches to "Download & Upload" if a source channel restricts forwarding.
* **Session Management:** Supports multiple Telegram accounts with an easy-to-use login interface.
* **Local Backup:** Optional feature to save all transferred media to your local drive.

---

## 🛠 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/xNabil/Telegram-Save-Restricted-Content.git
cd Telegram-Save-Restricted-Content.git

```

### 2. Install Dependencies

Ensure you have Python 3.8+ installed. Install the required libraries using `pip`:

```bash
pip install -r requirements.txt

```

### 3. Configure Environment Variables

Create a `.env` file in the root directory (or edit the existing one) with your Telegram API credentials and transfer settings.

**Required Settings:**

* `API_ID`: Your Telegram API ID from [my.telegram.org](https://my.telegram.org).
* `API_HASH`: Your Telegram API Hash.
* `SOURCES`: Comma-separated list of source IDs or usernames (e.g., `-100123,@source`).
* `DESTINATIONS`: Comma-separated list of destination IDs or usernames.

---

## ⚙️ Configuration (.env)

| Variable | Description | Default |
| --- | --- | --- |
| `PHOTOS` | Transfer photo messages. | `True` |
| `VIDEOS` | Transfer video messages. | `True` |
| `TEXT` | Transfer text-only messages. | `True` |
| `HIDE_SENDER` | If `True`, uses "Copy" instead of "Forward" to hide the original author. | `True` |
| `DROP_CAPTION` | Remove captions from media during transfer. | `False` |
| `SAVE_TO_LOCAL` | Save a copy of all media to the `/downloads` folder. | `False` |
| `FORWARDING` | Attempt to use Telegram's native forwarding (faster). | `True` |

---

## 📖 Usage

### 1. Start the Script

Run the main script:

```bash
python bot.py

```

### 2. Login

Choose **Option 1** to log in. You will be prompted for your phone number and the verification code sent via Telegram. If 2FA is enabled, you will also be asked for your password. This creates a `.session` file in the `/sessions` folder.

### 3. Run a Transfer

Choose **Option 2** and select your saved account. The script will:

1. Resolve your source and destination chats.
2. Ask for a **Message ID Range** (e.g., `500-1000`).
3. Process and transfer the messages in batches.

> **Note:** If you are transferring to or from a Forum Topic, use the format `chat_id:topic_id` in your `.env` file.

---
## 📂 How to Find Telegram IDs & Topic IDs

To fill out your `.env` file correctly, you need the unique identifiers for your chats.

### Finding Chat IDs

* 
**Usernames:** You can use public handles like `@channelname` or `@username`.


* **Private Chat IDs:** Use a bot like `@MissRose_bot` or `@IDBot`. Forward a message from the source to the bot, and it will return the ID (usually starting with `-100`).



### Finding Topic IDs (For Forums)

* 
**Right-Click Method:** On Telegram Desktop, right-click a message within the specific topic and select "Copy Post Link." 


* **Link Structure:** The link will look like `https://t.me/c/123456789/5/100`. In this example:
* `123456789` is the Chat ID.
* 
`5` is the **Topic ID** (the number you need for the `SOURCES` or `DESTINATIONS` field).

---

## 🛠 Troubleshooting Common Issues

| Issue | Solution |
| --- | --- |
| **"FloodWait" Error** | You are sending requests too fast. The script will automatically pause for the required time to avoid a ban.

 |
| **"CHAT_FORWARDS_RESTRICTED"** | The source channel has disabled forwarding. Ensure `HIDE_SENDER=True` and `FORWARDING_ONLY=False` so the script can download and re-upload the media instead.

 |
| **"MEDIA_EMPTY"** | Usually occurs if the source message was deleted during the transfer or if the session lacks permission to view the media.

 |
| **Missing Messages** | Ensure you are a member of both the source and destination chats before starting the transfer.

 |

---

## 💡 Pro-Tips for Large Transfers

* 
**Batching:** The script processes messages in batches of 200 to maintain stability.


* 
**Safety Delays:** Random sleep intervals (1.0 to 2.5 seconds) are built-in between messages to mimic human behavior and protect your account.


* 
**Local Backups:** Set `SAVE_TO_LOCAL=True` if you want to keep a hard copy of every file transferred on your computer.



## 📂 Project Structure

* `bot.py`: The main application logic.
* `sessions/`: Stores your encrypted Telegram session files and `accounts.json` cache.
* `downloads/`: Local storage for media if `SAVE_TO_LOCAL` is enabled.
* `requirements.txt`: List of Python dependencies (Pyrogram, Colorama, Tqdm, etc.).

---

## ⚠️ Disclaimer

This tool is for personal use and backup purposes. Please ensure you comply with Telegram's Terms of Service and respect the copyright of the content you are transferring.
