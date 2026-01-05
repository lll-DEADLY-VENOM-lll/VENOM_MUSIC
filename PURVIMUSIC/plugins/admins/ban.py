from pyrogram import filters, enums
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions
)
from pyrogram.errors.exceptions.bad_request_400 import (
    ChatAdminRequired,
    UserAdminInvalid,
    BadRequest
)
import datetime
from PURVIMUSIC import app

def mention(user, name, mention=True):
    if mention == True:
        link = f"[{name}](tg://openmessage?user_id={user})"
    else:
        link = f"[{name}](https://t.me/{user})"
    return link

async def get_userid_from_username(username):
    try:
        user = await app.get_users(username)
        return [user.id, user.first_name]
    except:
        return None

async def ban_user(user_id, first_name, admin_id, admin_name, chat_id, reason, time=None):
    try:
        await app.ban_chat_member(chat_id, user_id)
    except ChatAdminRequired:
        return "I need Ban Rights to perform this action! 😡", False
    except UserAdminInvalid:
        return "I cannot ban an administrator!", False
    except Exception as e:
        if user_id == (await app.get_me()).id:
            return "Why should I ban myself? I'm not that stupid.", False
        return f"Error: {e}", False

    user_mention = mention(user_id, first_name)
    admin_mention = mention(admin_id, admin_name)
    msg_text = f"{user_mention} was banned by {admin_mention}\n"
    if reason: msg_text += f"Reason: `{reason}`\n"
    if time: msg_text += f"Time: `{time}`\n"
    return msg_text, True

async def unban_user(user_id, first_name, admin_id, admin_name, chat_id):
    try:
        await app.unban_chat_member(chat_id, user_id)
    except ChatAdminRequired:
        return "I need admin rights to unban users!"
    except Exception as e:
        return f"Error: {e}"

    user_mention = mention(user_id, first_name)
    admin_mention = mention(admin_id, admin_name)
    return f"{user_mention} was unbanned by {admin_mention}"

async def mute_user(user_id, first_name, admin_id, admin_name, chat_id, reason, time=None):
    try:
        if time:
            mute_end_time = datetime.datetime.now() + time
            await app.restrict_chat_member(chat_id, user_id, ChatPermissions(), mute_end_time)
        else:
            await app.restrict_chat_member(chat_id, user_id, ChatPermissions())
    except ChatAdminRequired:
        return "I need Mute Rights to perform this action!", False
    except UserAdminInvalid:
        return "I cannot mute an administrator!", False
    except Exception as e:
        return f"Error: {e}", False

    user_mention = mention(user_id, first_name)
    admin_mention = mention(admin_id, admin_name)
    msg_text = f"{user_mention} was muted by {admin_mention}\n"
    if reason: msg_text += f"Reason: `{reason}`\n"
    return msg_text, True

async def unmute_user(user_id, first_name, admin_id, admin_name, chat_id):
    try:
        await app.restrict_chat_member(
            chat_id, user_id,
            ChatPermissions(
                can_send_media_messages=True,
                can_send_messages=True,
                can_send_other_messages=True,
                can_send_polls=True,
                can_add_web_page_previews=True,
                can_invite_users=True
            )
        )
    except ChatAdminRequired:
        return "I need admin rights to unmute users!"
    except Exception as e:
        return f"Error: {e}"

    user_mention = mention(user_id, first_name)
    admin_mention = mention(admin_id, admin_name)
    return f"{user_mention} was unmuted by {admin_mention}"

# --- HANDLERS ---

@app.on_message(filters.command(["ban"]))
async def ban_command_handler(client, message):
    chat = message.chat
    admin_id = message.from_user.id
    admin_name = message.from_user.first_name
    
    # FIX: Wrap get_member in try-except
    try:
        member = await chat.get_member(admin_id)
    except ChatAdminRequired:
        return await message.reply_text("I cannot check permissions because I am not an admin! Please promote me first.")

    if not (member.status == enums.ChatMemberStatus.ADMINISTRATOR or member.status == enums.ChatMemberStatus.OWNER):
        return await message.reply_text("You are not an admin!")
    
    if member.status == enums.ChatMemberStatus.ADMINISTRATOR and not member.privileges.can_restrict_members:
        return await message.reply_text("You don't have the 'Ban Users' permission.")

    if len(message.command) > 1:
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            first_name = message.reply_to_message.from_user.first_name
            reason = message.text.split(None, 1)[1]
        else:
            try:
                user_id = int(message.command[1])
                first_name = "User"
            except:
                user_obj = await get_userid_from_username(message.command[1])
                if not user_obj: return await message.reply_text("User not found.")
                user_id, first_name = user_obj[0], user_obj[1]
            reason = message.text.partition(message.command[1])[2] or None
    elif message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
        reason = None
    else:
        return await message.reply_text("Reply to a message or provide a User ID/Username to ban.")
        
    msg_text, result = await ban_user(user_id, first_name, admin_id, admin_name, chat.id, reason)
    await message.reply_text(msg_text)

@app.on_message(filters.command(["unban"]))
async def unban_command_handler(client, message):
    chat = message.chat
    admin_id = message.from_user.id
    
    try:
        member = await chat.get_member(admin_id)
    except ChatAdminRequired:
        return await message.reply_text("Make me admin first!")

    if not (member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]):
        return await message.reply_text("Admins only!")

    if len(message.command) > 1:
        try:
            user_id = int(message.command[1])
            first_name = "User"
        except:
            user_obj = await get_userid_from_username(message.command[1])
            if not user_obj: return await message.reply_text("User not found.")
            user_id, first_name = user_obj[0], user_obj[1]
    elif message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
    else:
        return await message.reply_text("Who should I unban?")
        
    msg_text = await unban_user(user_id, first_name, admin_id, message.from_user.first_name, chat.id)
    await message.reply_text(msg_text)

@app.on_message(filters.command(["mute"]))
async def mute_command_handler(client, message):
    chat = message.chat
    admin_id = message.from_user.id
    
    try:
        member = await chat.get_member(admin_id)
    except ChatAdminRequired:
        return await message.reply_text("I need admin rights to check your permissions!")

    if not (member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]):
        return await message.reply_text("You are not an admin!")

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
        reason = message.text.split(None, 1)[1] if len(message.command) > 1 else None
    elif len(message.command) > 1:
        user_obj = await get_userid_from_username(message.command[1])
        if not user_obj: return await message.reply_text("User not found.")
        user_id, first_name = user_obj[0], user_obj[1]
        reason = None
    else:
        return await message.reply_text("Reply to someone to mute them.")
    
    msg_text, result = await mute_user(user_id, first_name, admin_id, message.from_user.first_name, chat.id, reason)
    await message.reply_text(msg_text)

@app.on_message(filters.command(["unmute"]))
async def unmute_command_handler(client, message):
    chat = message.chat
    admin_id = message.from_user.id
    
    try:
        member = await chat.get_member(admin_id)
    except ChatAdminRequired:
        return await message.reply_text("Promote me to admin first!")

    if not (member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]):
        return await message.reply_text("Admins only!")

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
    elif len(message.command) > 1:
        user_obj = await get_userid_from_username(message.command[1])
        if not user_obj: return await message.reply_text("User not found.")
        user_id, first_name = user_obj[0], user_obj[1]
    else:
        return await message.reply_text("Reply to someone to unmute them.")
        
    msg_text = await unmute_user(user_id, first_name, admin_id, message.from_user.first_name, chat.id)
    await message.reply_text(msg_text)