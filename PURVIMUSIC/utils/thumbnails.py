import asyncio, os, re, httpx, aiofiles.os
from io import BytesIO 
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from aiofiles.os import path as aiopath
# Video को भी इम्पोर्ट करें
from youtubesearchpython.__future__ import VideosSearch, Video

from ..logging import LOGGER

def load_fonts():
    try:
        return {
            "cfont": ImageFont.truetype("PURVIMUSIC/assets/cfont.ttf", 24),
            "tfont": ImageFont.truetype("PURVIMUSIC/assets/font.ttf", 30),
        }
    except Exception as e:
        LOGGER.error(f"Font loading error: {e}, using default fonts")
        return {
            "cfont": ImageFont.load_default(),
            "tfont": ImageFont.load_default(),
        }

FONTS = load_fonts()
FALLBACK_IMAGE_PATH = "PURVIMUSIC/assets/controller.png"
YOUTUBE_IMG_URL = "https://i.ytimg.com/vi/default.jpg"

async def resize_youtube_thumbnail(img: Image.Image) -> Image.Image:
    target_width, target_height = 1280, 720
    img = img.convert("RGBA")
    aspect_ratio = img.width / img.height
    target_ratio = target_width / target_height

    if aspect_ratio > target_ratio:
        new_height = target_height
        new_width = int(new_height * aspect_ratio)
    else:
        new_width = target_width
        new_height = int(new_width / aspect_ratio)

    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    img = img.crop((left, top, left + target_width, top + target_height))
    return ImageEnhance.Sharpness(img).enhance(1.5)

async def fetch_image(url: str) -> Image.Image:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            return await resize_youtube_thumbnail(img)
        except Exception as e:
            LOGGER.error(f"Image load error: {e}")
            if os.path.exists(FALLBACK_IMAGE_PATH):
                img = Image.open(FALLBACK_IMAGE_PATH).convert("RGBA")
                return await resize_youtube_thumbnail(img)
            return Image.new("RGBA", (1280, 720), (20, 20, 20, 255))

def clean_text(text: str, limit: int = 25) -> str:
    if not text: return "Unknown"
    text = text.strip()
    return f"{text[:limit-3]}..." if len(text) > limit else text

async def add_controls(img: Image.Image) -> Image.Image:
    # Background Blur
    bg = img.filter(ImageFilter.GaussianBlur(radius=15))
    bg = ImageEnhance.Brightness(bg).enhance(0.5)
    
    draw = ImageDraw.Draw(bg)
    # Box design
    draw.rounded_rectangle((305, 125, 975, 595), radius=25, fill=(0, 0, 0, 140))
    
    try:
        if os.path.exists("PURVIMUSIC/assets/controls.png"):
            con = Image.open("PURVIMUSIC/assets/controls.png").convert("RGBA")
            con = con.resize((600, 160), Image.Resampling.LANCZOS)
            bg.paste(con, (340, 415), con)
    except: pass
    return bg

def make_rounded_rectangle(image: Image.Image, size: tuple = (200, 200)) -> Image.Image:
    image = ImageOps.fit(image, size, centering=(0.5, 0.5))
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=25, fill=255)
    image.putalpha(mask)
    return image

async def get_thumb(videoid: str) -> str:
    if not videoid: return ""
    save_dir = f"database/photos/{videoid}.png"
    
    if not os.path.exists("database/photos"):
        os.makedirs("database/photos", exist_ok=True)

    title, artist, thumb_url = "Unknown Title", "Unknown Artist", ""

    # --- METADATA FETCHING (FIXED) ---
    try:
        # Method 1: direct Video Info (Sabse fast aur accurate)
        video_data = await Video.getInfo(f"https://www.youtube.com/watch?v={videoid}")
        if video_data:
            title = video_data.get("title", "Unknown")
            artist = video_data.get("channel", {}).get("name", "Unknown Artist")
            thumbnails = video_data.get("thumbnails", [])
            thumb_url = thumbnails[-1]["url"].split("?")[0] if thumbnails else f"https://img.youtube.com/vi/{videoid}/maxresdefault.jpg"
    except Exception as e:
        LOGGER.error(f"Method 1 failed: {e}")
        try:
            # Method 2: Search Fallback
            results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
            resp = await results.next()
            if resp and "result" in resp and len(resp["result"]) > 0:
                res = resp["result"][0]
                title = res.get("title", "Unknown")
                artist = res.get("channel", {}).get("name", "Unknown")
                thumb_url = res.get("thumbnails", [{}])[0].get("url", "").split("?")[0]
        except Exception as e2:
            LOGGER.error(f"Method 2 failed: {e2}")
            thumb_url = f"https://img.youtube.com/vi/{videoid}/maxresdefault.jpg"

    # --- IMAGE PROCESSING ---
    try:
        raw_img = await fetch_image(thumb_url)
        bg = await add_controls(raw_img)
        rounded_art = make_rounded_rectangle(raw_img, size=(210, 210))
        
        bg.paste(rounded_art, (340, 165), rounded_art)
        
        draw = ImageDraw.Draw(bg)
        draw.text((570, 180), clean_text(title, 25), (255, 255, 255), font=FONTS["tfont"])
        draw.text((570, 230), clean_text(artist, 30), (200, 200, 200), font=FONTS["cfont"])

        bg = bg.convert("RGB")
        bg.save(save_dir, "JPEG", quality=90) # PNG ki jagah JPEG use karein fast loading ke liye
        
        raw_img.close()
        bg.close()
        return save_dir
    except Exception as e:
        LOGGER.error(f"Thumbnail generation error: {e}")
        return ""
