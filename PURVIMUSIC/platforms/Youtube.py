import asyncio
import os
import re
import logging
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config 
from PURVIMUSIC.utils.formatters import time_to_seconds

logger = logging.getLogger(__name__)

# --- FIX: Config se sahi variables uthana ---
# Hum teeno keys ko ek list mein daal rahe hain
API_KEYS = [k for k in [
    getattr(config, "YT_API_KEY_1", None),
    getattr(config, "YT_API_KEY_2", None),
    getattr(config, "YT_API_KEY_3", None)
] if k]

current_key_index = 0

def get_youtube_client():
    global current_key_index
    if not API_KEYS:
        return None
    if current_key_index >= len(API_KEYS):
        current_key_index = 0 
    return build("youtube", "v3", developerKey=API_KEYS[current_key_index], static_discovery=False)

cookies_file = getattr(config, "COOKIES_FILE_PATH", "PURVIMUSIC/cookies.txt")
if not os.path.exists(cookies_file):
    cookies_file = None

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="

    def parse_duration(self, duration):
        if not duration: return "00:00", 0
        match = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        hours, minutes, seconds = [int(match.group(i) or 0) for i in range(1, 4)]
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return (f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"), total_seconds

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1, message_1.reply_to_message] if message_1.reply_to_message else [message_1]
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        return (message.text or message.caption)[entity.offset : entity.offset + entity.length]
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        return bool(re.search(self.regex, link))

    async def fetch_with_quota_check(self, service_type, **kwargs):
        global current_key_index
        while current_key_index < len(API_KEYS):
            try:
                youtube = get_youtube_client()
                if not youtube: break
                if service_type == "search":
                    return await asyncio.to_thread(youtube.search().list(**kwargs).execute)
                elif service_type == "videos":
                    return await asyncio.to_thread(youtube.videos().list(**kwargs).execute)
            except HttpError as e:
                if e.resp.status == 403: # Quota Limit Error
                    logger.warning(f"API Key {current_key_index + 1} exhausted. Switching...")
                    current_key_index += 1
                else:
                    break
        return None

    async def ytdl_fallback(self, query):
        loop = asyncio.get_running_loop()
        ydl_opts = {"quiet": True, "no_warnings": True, "format": "bestaudio/best", "skip_download": True}
        if cookies_file: ydl_opts["cookiefile"] = cookies_file
        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_query = query if re.search(self.regex, query) else f"ytsearch1:{query}"
                return ydl.extract_info(search_query, download=False)
        try:
            info = await loop.run_in_executor(None, extract)
            if "entries" in info: info = info["entries"][0]
            d_str = f"{info['duration'] // 60:02d}:{info['duration'] % 60:02d}"
            return info["title"], d_str, info["duration"], info["thumbnail"], info["id"]
        except: return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if API_KEYS:
            vidid = link if videoid else (re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", link).group(1) if re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", link) else None)
            if not vidid:
                search_res = await self.fetch_with_quota_check("search", q=link, part="id", maxResults=1, type="video")
                if search_res and search_res.get("items"):
                    vidid = search_res["items"][0]["id"]["videoId"]
            if vidid:
                video_res = await self.fetch_with_quota_check("videos", part="snippet,contentDetails", id=vidid)
                if video_res and video_res.get("items"):
                    data = video_res["items"][0]
                    d_str, _ = self.parse_duration(data["contentDetails"]["duration"])
                    return data["snippet"]["title"], d_str, None, data["snippet"]["thumbnails"]["high"]["url"], vidid
        return await self.ytdl_fallback(link)

    async def title(self, link: str, videoid: Union[bool, str] = None):
        res = await self.details(link, videoid)
        return res[0] if res else "Unknown"

    async def track(self, link: str, videoid: Union[bool, str] = None):
        res = await self.details(link, videoid)
        if not res: return None, None
        title, d_min, _, thumb, vidid = res
        return {"title": title, "link": self.base + vidid, "vidid": vidid, "duration_min": d_min, "thumb": thumb}, vidid

    async def download(self, link: str, mystic, video=None, videoid=None, songaudio=None, songvideo=None, format_id=None, title=None) -> str:
        if videoid: link = self.base + link
        loop = asyncio.get_running_loop()
        def dl():
            opts = {"format": "bestaudio/best", "outtmpl": "downloads/%(id)s.%(ext)s", "quiet": True}
            if cookies_file: opts["cookiefile"] = cookies_file
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return os.path.join("downloads", f"{info['id']}.{info['ext']}")
        return await loop.run_in_executor(None, dl)
