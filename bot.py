import os
import json
import asyncio
import random
from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.errors import (
    PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded,
    ChatForwardsRestricted, ChannelPrivate, ChatWriteForbidden, ChannelInvalid,
    FloodWait, MediaEmpty, BadRequest
)
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from pyrogram.enums import ParseMode
from colorama import Fore, Style, init
from tqdm import tqdm

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
SAVE_TO_LOCAL = os.getenv("SAVE_TO_LOCAL", "False").lower() == "true"
FORWARDING = os.getenv("FORWARDING", "True").lower() == "true"
FORWARDING_ONLY = os.getenv("FORWARDING_ONLY", "False").lower() == "true"

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
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=4)

def update_account_cache(session_name, user):
    """Update account cache with current user info"""
    accounts = load_accounts()
    updated_info = {
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "username": user.username or "None",
        "id": user.id
    }
    if accounts.get(session_name) != updated_info:
        accounts[session_name] = updated_info
        save_accounts(accounts)

async def create_session():
    session_name = input(Fore.GREEN + Style.BRIGHT + "Enter a name for the new session (e.g., account1): " + Style.RESET_ALL).strip()
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
        print(Fore.YELLOW + Style.BRIGHT + "Enter your phone number (with country code, e.g. +1234567890): " + Style.RESET_ALL)
        phone = input().strip()
        sent_code = await client.send_code(phone)
        
        print(Fore.YELLOW + Style.BRIGHT + "Enter the login code you received: " + Style.RESET_ALL)
        code = input().strip()
        
        try:
            await client.sign_in(phone, sent_code.phone_code_hash, code)
        except SessionPasswordNeeded:
            print(Fore.YELLOW + Style.BRIGHT + "2FA enabled. Enter your password: " + Style.RESET_ALL)
            password = input().strip()
            await client.sign_in(password=password)
        
        user = await client.get_me()
        update_account_cache(session_name, user)
        
        print(Fore.GREEN + Style.BRIGHT + f"Login successful: {user.first_name} {'@' + user.username if user.username else ''} - ID {user.id} - {session_name}.session" + Style.RESET_ALL)
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
        print(Fore.YELLOW + Style.BRIGHT + "No sessions found. Please create one first." + Style.RESET_ALL)
        return None
    
    print(Fore.CYAN + Style.BRIGHT + "\nAvailable accounts:" + Style.RESET_ALL)
    for i, name in enumerate(session_names, 1):
        acc = accounts.get(name, {"first_name": "Unknown", "username": "None", "id": "?"})
        print(Fore.MAGENTA + f"{i}. {acc['first_name']} - @{acc['username']} - ID {acc['id']} - {name}.session" + Style.RESET_ALL)
    
    try:
        choice = int(input(Fore.GREEN + Style.BRIGHT + "\nSelect account number: " + Style.RESET_ALL))
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
            print(Fore.CYAN + Style.BRIGHT + f"Resolved @{chat} → ID: {resolved.id} (Title: {resolved.title or resolved.username})" + Style.RESET_ALL)
            return resolved.id, topic_id, resolved.title or resolved.username
        else:
            chat_id = int(chat)
            resolved = await client.get_chat(chat_id)
            print(Fore.CYAN + Style.BRIGHT + f"Chat ID {chat} resolved → Title: {resolved.title or resolved.username}" + Style.RESET_ALL)
            return chat_id, topic_id, resolved.title or resolved.username
    except ChannelPrivate:
        print(Fore.RED + f"You are not a member or banned from this channel/group: {chat}" + Style.RESET_ALL)
    except ChannelInvalid:
        print(Fore.RED + f"Invalid channel/group ID or peer not known: {chat}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error resolving {chat}: {e}" + Style.RESET_ALL)
    return None, None, None

async def process_group(client, messages, dest_chats, src_title, src_topic):
    if not messages:
        return
    
    first_msg = messages[0]
    
    # Check if we should process this group based on media type filters
    has_photo = any(m.photo for m in messages)
    has_video = any(m.video for m in messages)
    has_text = any(m.text or m.caption for m in messages)
    
    should_process = (PHOTOS and has_photo) or (VIDEOS and has_video) or (TEXT and has_text)
    
    if not should_process:
        return
    
    for dest_chat_id, dest_topic in dest_chats:
        try:
            kwargs = {}
            if dest_topic:
                kwargs["reply_to_message_id"] = dest_topic
            
            forwarded_or_copied = False
            
            # --- STRATEGY 1: Internal Forward/Copy (when FORWARDING=True or FORWARDING_ONLY=True) ---
            if FORWARDING or FORWARDING_ONLY:
                try:
                    if HIDE_SENDER:
                        # For albums (multiple messages with media_group_id), use copy_media_group
                        if len(messages) > 1:
                            # Copy entire album - preserves grid/album structure
                            await client.copy_media_group(
                                chat_id=dest_chat_id,
                                from_chat_id=first_msg.chat.id,
                                message_id=first_msg.id,
                                captions="" if DROP_CAPTION else None,
                                **kwargs
                            )
                        else:
                            # Single message - use copy_message
                            caption = "" if DROP_CAPTION else None
                            await client.copy_message(
                                chat_id=dest_chat_id,
                                from_chat_id=first_msg.chat.id,
                                message_id=first_msg.id,
                                caption=caption,
                                **kwargs
                            )
                        forwarded_or_copied = True
                    else:
                        # Forward with author - preserves albums automatically
                        await client.forward_messages(
                            chat_id=dest_chat_id,
                            from_chat_id=first_msg.chat.id,
                            message_ids=[m.id for m in messages],
                            drop_author=False,
                            **kwargs
                        )
                        forwarded_or_copied = True
                    
                    # If SAVE_TO_LOCAL is enabled, download even after forwarding
                    if SAVE_TO_LOCAL and forwarded_or_copied:
                        safe_title = src_title.replace(" ", "_").replace("/", "_").replace("|", "_").replace("\\", "_").replace(":", "_")
                        save_dir = os.path.join("downloads", safe_title)
                        os.makedirs(save_dir, exist_ok=True)
                        for message in messages:
                            if message.photo or message.video:
                                ext = ".jpg" if message.photo else ".mp4"
                                permanent_path = os.path.join(save_dir, f"{message.id}{ext}")
                                await message.download(permanent_path)
                    
                    # Successfully handled via forward/copy, skip to next destination
                    if forwarded_or_copied:
                        continue
                
                except ChatForwardsRestricted:
                    if FORWARDING_ONLY:
                        print(Fore.YELLOW + f"Forwarding failed for group {first_msg.id}, skipping due to FORWARDING_ONLY." + Style.RESET_ALL)
                        return
                    # If not FORWARDING_ONLY, continue to Strategy 2 (download & upload)
                except Exception as e:
                    if FORWARDING_ONLY:
                        print(Fore.RED + f"Forwarding failed for group {first_msg.id}: {e}" + Style.RESET_ALL)
                        return
                    # If not FORWARDING_ONLY, continue to Strategy 2
            
            # --- STRATEGY 2: Download & Upload (only if Strategy 1 failed and FORWARDING_ONLY=False) ---
            if not FORWARDING_ONLY and not forwarded_or_copied:
                save_dir = None
                file_paths = []
                media_list = []
                caption_set = False
                
                if SAVE_TO_LOCAL:
                    safe_title = src_title.replace(" ", "_").replace("/", "_").replace("|", "_").replace("\\", "_").replace(":", "_")
                    save_dir = os.path.join("downloads", safe_title)
                    os.makedirs(save_dir, exist_ok=True)
                
                for message in messages:
                    caption = None if DROP_CAPTION else (message.caption or message.text)
                    entities = message.caption_entities or message.entities
                    
                    if message.photo or message.video:
                        ext = ".jpg" if message.photo else ".mp4"
                        
                        if SAVE_TO_LOCAL:
                            file_path = os.path.join(save_dir, f"{message.id}{ext}")
                        else:
                            file_path = os.path.join("downloads", f"temp_{'p' if message.photo else 'v'}_{message.id}{ext}")
                            file_paths.append(file_path)
                        
                        await message.download(file_path)
                        
                        # Create InputMedia for the album
                        if message.photo:
                            media = InputMediaPhoto(file_path)
                        else:
                            media = InputMediaVideo(file_path)
                        
                        # Add caption only to the first media in the group
                        if caption and not caption_set:
                            media.caption = caption
                            media.parse_mode = ParseMode.HTML if entities else None
                            caption_set = True
                        
                        media_list.append(media)
                
                # Send as media group (album) if we have media
                if media_list:
                    try:
                        await client.send_media_group(dest_chat_id, media_list, **kwargs)
                    except (MediaEmpty, BadRequest) as e:
                        if "MEDIA_EMPTY" in str(e):
                            print(Fore.YELLOW + f"{first_msg.id} - [400 MEDIA_EMPTY]" + Style.RESET_ALL)
                        else:
                            raise
                
                # Cleanup temp files if not saving
                if not SAVE_TO_LOCAL:
                    for file_path in file_paths:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                
                # Handle text-only messages (not part of media group)
                if not media_list and first_msg.text:
                    await client.send_message(
                        dest_chat_id, 
                        first_msg.text,
                        parse_mode=ParseMode.HTML if first_msg.entities else None,
                        **kwargs
                    )
        
        except FloodWait as e:
            print(Fore.YELLOW + f"FloodWait: sleeping {e.value} seconds..." + Style.RESET_ALL)
            await asyncio.sleep(e.value + 2)
        except ChannelPrivate:
            print(Fore.RED + f"Can't write to private destination: {dest_chat_id}" + Style.RESET_ALL)
        except ChatWriteForbidden:
            print(Fore.RED + f"No permission to send in destination: {dest_chat_id}" + Style.RESET_ALL)
        except Exception as e:
            if "MEDIA_EMPTY" in str(e):
                print(Fore.YELLOW + f"{first_msg.id} - [400 MEDIA_EMPTY]" + Style.RESET_ALL)
            else:
                print(Fore.RED + f"Error sending group {first_msg.id}: {e}" + Style.RESET_ALL)
        
        await asyncio.sleep(random.uniform(1.0, 2.5))

async def transfer_content(client: Client):
    # Update account cache on every session start
    me = await client.get_me()
    session_name = client.name
    update_account_cache(session_name, me)
    
    print(Fore.YELLOW + Style.BRIGHT + "Loading dialogs to cache chats/channels..." + Style.RESET_ALL)
    async for _ in client.get_dialogs():
        pass
    print(Fore.GREEN + Style.BRIGHT + "Dialogs loaded." + Style.RESET_ALL)
    
    dest_chats = []
    for dest in DESTINATIONS:
        resolved_id, resolved_topic, _ = await resolve_chat(client, dest)
        if resolved_id:
            dest_chats.append((resolved_id, resolved_topic))
    
    if not dest_chats:
        print(Fore.RED + Style.BRIGHT + "No valid destinations resolved. Check DESTINATIONS in .env." + Style.RESET_ALL)
        return
    
    for source in SOURCES:
        src_id, src_topic, src_title = await resolve_chat(client, source)
        if not src_id:
            continue
        
        get_kwargs = {}
        if src_topic:
            get_kwargs["reply_to_message_id"] = src_topic
        
        print(Fore.CYAN + Style.BRIGHT + f"\nProcessing source: {src_id} (topic: {src_topic or 'general'}, title: {src_title})" + Style.RESET_ALL)
        print(Fore.GREEN + Style.BRIGHT + "[ Example: 1-100 ]" + Style.RESET_ALL)
        input_str = input(Fore.GREEN + Style.BRIGHT + "Please enter message ID range: " + Style.RESET_ALL).strip()
        
        try:
            parts = input_str.split("-")
            if len(parts) != 2:
                raise ValueError
            start_id = int(parts[0].strip())
            end_id = int(parts[1].strip())
        except:
            print(Fore.RED + "Invalid format. Use 1-100." + Style.RESET_ALL)
            continue
        
        if start_id > end_id:
            print(Fore.RED + "Start ID cannot be greater than end ID." + Style.RESET_ALL)
            continue
        
        total_messages = end_id - start_id + 1
        print(Fore.YELLOW + Style.BRIGHT + f"Transferring messages {start_id} → {end_id} ({total_messages} messages)" + Style.RESET_ALL)
        
        batch_size = 200
        batches = []
        current_start = start_id
        
        while current_start <= end_id:
            current_end = min(current_start + batch_size - 1, end_id)
            batches.append((current_start, current_end))
            current_start = current_end + 1
        
        for batch_start, batch_end in batches:
            print(Fore.YELLOW + Style.BRIGHT + f"Processing batch {batch_start} → {batch_end}" + Style.RESET_ALL)
            
            # Fetch messages in chunks
            msg_ids = list(range(batch_start, batch_end + 1))
            messages = []
            
            for i in range(0, len(msg_ids), 100):
                chunk = msg_ids[i:i+100]
                chunk_msgs = await client.get_messages(src_id, chunk, **get_kwargs)
                if chunk_msgs is None:
                    continue
                if not isinstance(chunk_msgs, list):
                    chunk_msgs = [chunk_msgs]
                messages.extend([m for m in chunk_msgs if m and not m.empty])
            
            # Group by media_group_id (albums) or individual messages
            groups = {}
            for message in messages:
                # Use media_group_id for albums, or unique ID for single messages
                group_id = message.media_group_id if message.media_group_id else f"single_{message.id}"
                if group_id not in groups:
                    groups[group_id] = []
                groups[group_id].append(message)
            
            total_groups = len(groups)
            
            with tqdm(total=total_groups, desc=Fore.BLUE + Style.BRIGHT + "Transferring", unit="group",
                      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]" + Style.RESET_ALL) as pbar:
                for group_id, msgs in groups.items():
                    # Sort messages by ID to maintain order in albums
                    msgs.sort(key=lambda m: m.id)
                    await process_group(client, msgs, dest_chats, src_title, src_topic)
                    pbar.update(1)
            
            print(Fore.CYAN + Style.BRIGHT + f"Finished batch {batch_start} → {batch_end}: {total_groups} groups processed." + Style.RESET_ALL)
            await asyncio.sleep(random.uniform(5.0, 10.0))
        
        print(Fore.CYAN + Style.BRIGHT + f"Finished source '{src_title}'." + Style.RESET_ALL)

async def main():
    print(
    Fore.CYAN + Style.BRIGHT +
    "\n╔══════════════════════════════════════════╗\n"
    "║   Telegram Message Transfer Tool v2.7    ║\n"
    "║   GitHub: https://github.com/xNabil/     ║\n"
    "╚══════════════════════════════════════════╝\n"
    + Style.RESET_ALL
)

    print(Fore.CYAN + Style.BRIGHT + "1. Login (Create new session)\n2. Start Transfer\n" + Style.RESET_ALL)
    choice = input(Fore.GREEN + Style.BRIGHT + "Choose (1 or 2): " + Style.RESET_ALL).strip()
    
    if choice == "1":
        await create_session()
    elif choice == "2":
        session_name = await list_sessions()
        if not session_name:
            return
        
        client = Client(name=session_name, api_id=API_ID, api_hash=API_HASH, workdir="sessions")
        async with client:
            me = await client.get_me()
            print(Fore.GREEN + Style.BRIGHT +
                  f"Logged in successfully as {me.first_name} {'@' + me.username if me.username else ''}. Starting transfer...\n" + Style.RESET_ALL)
            await transfer_content(client)
    else:
        print(Fore.RED + "Invalid option." + Style.RESET_ALL)

if __name__ == "__main__":
    asyncio.run(main())
