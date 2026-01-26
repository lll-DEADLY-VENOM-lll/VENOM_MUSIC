from pyrogram.types import InlineKeyboardButton
import config
from PURVIMUSIC import app

def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true"
            ),
            InlineKeyboardButton(text=_["S_B_2"], url=config.SUPPORT_CHAT),
        ],
    ]
    return buttons


def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                url=f"https://t.me/{app.username}?startgroup=true",
            )
        ],
        [
            # YAHAN CHANGE KIYA GAYA HAI: user_id ko hata kar tg:// user link dala gaya hai
            InlineKeyboardButton(
                text=_["S_B_5"], url=f"tg://openmessage?user_id={config.OWNER_ID}"
            ),
            InlineKeyboardButton(text=_["S_B_6"], url=config.SUPPORT_CHANNEL),
        ],
        [
            InlineKeyboardButton(text=_["S_B_4"], callback_data="settings_back_helper"),
        ],
    ]
    return buttons
