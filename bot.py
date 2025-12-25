import os
import json
import asyncio
import random
from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.errors import (
    PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded,
    ChatForwardsRestricted, ChannelPrivate, ChatWriteForbidden, ChannelInvalid
)
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from colorama import Fore, Style, init

init(autoreset=True)

# Create directories
os.makedirs("sessions", exist_ok=True)
os.makedirs("downloads", exist_ok=True)

# Load .env
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SOURCES_STR = os.getenv("SOURCES", "")
DESTINATIONS_STR = os.getenv("DESTINATIONS", "")
VIDEOS = os.getenv("VIDEOS", "True").lower() == "true"
PHOTOS = os.getenv("PHOTOS", "True").lower() == "true"
TEXT = os.getenv("TEXT", "True").lower() == "true"
HIDE_SENDER = os.getenv("HIDE_SENDER", "True").lower() == "true"
DROP_CAPTION = os.getenv("DROP_CAPTION", "False").lower() == "true"

# Parse chats
def parse_chats(chat_str):
    chats = []
    if chat_str:
        for item in chat_str.split(","):
            item = item.strip()
            if ":" in item:
                chat, topic = item.split(":", 1)
                chats.append((chat, int(topic)))
            else:
                chats.append((item, None))
    return chats

SOURCES = parse_chats(SOURCES_STR)
DESTINATIONS = parse_chats(DESTINATIONS_STR)

ACCOUNTS_FILE = os.path.join("sessions", "accounts.json")

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=4)

async def create_session():
    session_name = input(Fore.GREEN + "Enter a name for the new session (e.g., account1): " + Style.RESET_ALL).strip()
    if not session_name:
        print(Fore.RED + "Session name cannot be empty." + Style.RESET_ALL)
        return

    session_path = os.path.join("sessions", f"{session_name}.session")
    if os.path.exists(session_path):
        print(Fore.RED + f"Session '{session_name}' already exists." + Style.RESET_ALL)
        return

    client = Client(name=session_name, api_id=API_ID, api_hash=API_HASH, workdir="sessions")

    await client.connect()

    try:
        print(Fore.YELLOW + "Enter your phone number (with country code, e.g. +1234567890): " + Style.RESET_ALL)
        phone = input().strip()

        sent_code = await client.send_code(phone)
        print(Fore.YELLOW + "Enter the login code you received: " + Style.RESET_ALL)
        code = input().strip()

        try:
            await client.sign_in(phone, sent_code.phone_code_hash, code)
        except SessionPasswordNeeded:
            print(Fore.YELLOW + "2FA enabled. Enter your password: " + Style.RESET_ALL)
            password = input().strip()
            await client.sign_in(phone, sent_code.phone_code_hash, code, password=password)

        user = await client.get_me()

        accounts = load_accounts()
        accounts[session_name] = {
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "username": user.username or "None",
            "id": user.id
        }
        save_accounts(accounts)

        print(Fore.GREEN + f"Login successful: {user.first_name} {'@' + user.username if user.username else ''} - ID {user.id} - {session_name}.session" + Style.RESET_ALL)

    except PhoneCodeInvalid:
        print(Fore.RED + "Invalid code." + Style.RESET_ALL)
    except PhoneCodeExpired:
        print(Fore.RED + "Code expired." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Login failed: {e}" + Style.RESET_ALL)
    finally:
        await client.disconnect()

async def list_sessions():
    accounts = load_accounts()
    session_files = [f for f in os.listdir("sessions") if f.endswith(".session")]
    session_names = [os.path.splitext(f)[0] for f in session_files]

    if not session_names:
        print(Fore.YELLOW + "No sessions found. Please create one first." + Style.RESET_ALL)
        return None

    print(Fore.CYAN + "\nAvailable accounts:" + Style.RESET_ALL)
    for i, name in enumerate(session_names, 1):
        acc = accounts.get(name, {"first_name": "Unknown", "username": "None", "id": "?"})
        print(f"{i}. {acc['first_name']} - @{acc['username']} - ID {acc['id']} - {name}.session")

    try:
        choice = int(input(Fore.GREEN + "\nSelect account number: " + Style.RESET_ALL))
        if 1 <= choice <= len(session_names):
            return session_names[choice - 1]
    except ValueError:
        pass
    print(Fore.RED + "Invalid choice." + Style.RESET_ALL)
    return None

async def resolve_chat(client, chat_spec):
    chat, topic_id = chat_spec
    try:
        if str(chat).startswith("@"):
            resolved = await client.get_chat(chat)
            print(Fore.CYAN + f"Resolved @{chat} → ID: {resolved.id} (Title: {resolved.title or resolved.username})" + Style.RESET_ALL)
            return resolved.id, topic_id
        else:
            chat_id = int(chat)
            resolved = await client.get_chat(chat_id)
            print(Fore.CYAN + f"Chat ID {chat} resolved → Title: {resolved.title or resolved.username}" + Style.RESET_ALL)
            return chat_id, topic_id
    except ChannelPrivate:
        print(Fore.RED + f"You are not a member or banned from this channel/group: {chat}" + Style.RESET_ALL)
    except ChannelInvalid:
        print(Fore.RED + f"Invalid channel/group ID or peer not known: {chat}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error resolving {chat}: {e}" + Style.RESET_ALL)
    return None, None

async def process_message(client, message: Message, dest_chats):
    if not message:
        return

    if (PHOTOS and message.photo) or (VIDEOS and message.video) or (TEXT and (message.text or message.caption)):
        for dest_chat_id, dest_topic in dest_chats:
            try:
                caption = None if DROP_CAPTION else (message.caption or message.text)
                entities = message.caption_entities or message.entities

                kwargs = {
                    "caption": caption,
                    "parse_mode": ParseMode.HTML if entities else None
                }
                if dest_topic:
                    kwargs["reply_to_message_id"] = dest_topic  # For topics: use reply_to_message_id = topic_id

                if HIDE_SENDER:
                    await client.copy_message(
                        chat_id=dest_chat_id,
                        from_chat_id=message.chat.id,
                        message_id=message.id,
                        **kwargs
                    )
                else:
                    await client.forward_messages(
                        chat_id=dest_chat_id,
                        from_chat_id=message.chat.id,
                        message_ids=[message.id],
                        **kwargs
                    )
                print(Fore.GREEN + f"Sent message {message.id} → {dest_chat_id}:{dest_topic or 'general'}" + Style.RESET_ALL)
            except ChatForwardsRestricted:
                print(Fore.YELLOW + f"Forward restricted → downloading message {message.id}" + Style.RESET_ALL)
                try:
                    file_path = None
                    send_kwargs = kwargs.copy()
                    if dest_topic:
                        send_kwargs["reply_to_message_id"] = dest_topic

                    if message.photo:
                        file_path = await message.download(os.path.join("downloads", f"p_{message.id}.jpg"))
                        await client.send_photo(dest_chat_id, file_path, **send_kwargs)
                    elif message.video:
                        file_path = await message.download(os.path.join("downloads", f"v_{message.id}.mp4"))
                        await client.send_video(dest_chat_id, file_path, **send_kwargs)
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                    if message.text and not (message.photo or message.video):
                        await client.send_message(dest_chat_id, message.text, **send_kwargs)
                    print(Fore.GREEN + f"Uploaded media/text {message.id}" + Style.RESET_ALL)
                except Exception as e:
                    print(Fore.RED + f"Upload failed {message.id}: {e}" + Style.RESET_ALL)
            except ChannelPrivate:
                print(Fore.RED + f"Can't write to private destination: {dest_chat_id}" + Style.RESET_ALL)
            except ChatWriteForbidden:
                print(Fore.RED + f"No permission to send in destination: {dest_chat_id}" + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"Error sending {message.id}: {e}" + Style.RESET_ALL)

            await asyncio.sleep(random.uniform(1.0, 2.0))

async def transfer_content(client: Client):
    print(Fore.YELLOW + "Loading your dialogs to cache chats/channels..." + Style.RESET_ALL)
    async for _ in client.get_dialogs():
        pass
    print(Fore.GREEN + "Dialogs loaded." + Style.RESET_ALL)

    dest_chats = []
    for dest in DESTINATIONS:
        resolved = await resolve_chat(client, dest)
        if resolved[0]:
            dest_chats.append(resolved)

    if not dest_chats:
        print(Fore.RED + "No valid destinations resolved. Check your DESTINATIONS in .env and make sure your account has permission to post there." + Style.RESET_ALL)
        return

    for source in SOURCES:
        src_id, src_topic = await resolve_chat(client, source)
        if not src_id:
            continue

        print(Fore.CYAN + f"\nProcessing source: {src_id} (topic: {src_topic or 'general'})" + Style.RESET_ALL)

        try:
            start_id = int(input(Fore.GREEN + "Enter start message ID (from t.me link, e.g. 6): " + Style.RESET_ALL))
            end_id = int(input(Fore.GREEN + "Enter end message ID (from t.me link, e.g. 173): " + Style.RESET_ALL))
        except ValueError:
            print(Fore.RED + "Invalid message IDs entered. Skipping this source." + Style.RESET_ALL)
            continue

        if start_id > end_id:
            print(Fore.RED + "Start ID cannot be greater than end ID." + Style.RESET_ALL)
            continue

        print(Fore.YELLOW + f"Attempting to transfer messages {start_id} to {end_id}..." + Style.RESET_ALL)

        successful = 0
        skipped = 0

        for msg_id in range(start_id, end_id + 1):
            try:
                # Removed message_thread_id from get_messages (not supported in current Pyrogram)
                message = await client.get_messages(src_id, msg_id)
                if message:
                    await process_message(client, message, dest_chats)
                    successful += 1
                else:
                    print(Fore.YELLOW + f"Message {msg_id} returned empty (deleted?). Skipping." + Style.RESET_ALL)
                    skipped += 1
            except Exception as e:
                print(Fore.YELLOW + f"Message {msg_id} inaccessible (deleted or error: {str(e)[:100]}). Skipping." + Style.RESET_ALL)
                skipped += 1

        print(Fore.CYAN + f"Finished source {src_id}: {successful} sent, {skipped} skipped." + Style.RESET_ALL)

async def main():
    print(Fore.CYAN + "\n1. Login (Create new session)\n2. Start Transfer\n" + Style.RESET_ALL)
    choice = input(Fore.GREEN + "Choose (1 or 2): " + Style.RESET_ALL).strip()

    if choice == "1":
        await create_session()
    elif choice == "2":
        session_name = await list_sessions()
        if not session_name:
            return

        client = Client(name=session_name, api_id=API_ID, api_hash=API_HASH, workdir="sessions")

        async with client:
            accounts = load_accounts()
            if session_name not in accounts:
                user = await client.get_me()
                accounts[session_name] = {
                    "first_name": user.first_name or "",
                    "username": user.username or "None",
                    "id": user.id
                }
                save_accounts(accounts)

            print(Fore.GREEN + f"Logged in successfully. Starting transfer...\n" + Style.RESET_ALL)
            await transfer_content(client)
    else:
        print(Fore.RED + "Invalid option." + Style.RESET_ALL)

if __name__ == "__main__":
    asyncio.run(main())