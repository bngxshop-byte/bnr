from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

app = Flask(__name__)

AVATAR_SIZE = (125, 125)
FONT_PRIMARY = "Tajawal-Bold.ttf"
FONT_FALLBACKS = [
    "DejaVuSans.ttf",
    "NotoSans-Regular.ttf",
    "ARIAL.TTF",
    "NotoSansArabic-Regular.ttf",
    "NotoSansSymbols2-Regular.ttf",
    "NotoSansCJKjp-Regular.otf",
    "unifont-15.0.01.ttf"
]
SECRET_KEY = "BNGX"

# تحميل الخطوط مسبقًا
def load_fonts(sizes):
    fonts = {"primary": {}, "fallbacks": []}
    for size in sizes:
        try:
            fonts["primary"][size] = ImageFont.truetype(FONT_PRIMARY, size)
        except:
            fonts["primary"][size] = ImageFont.load_default()
    for font_path in FONT_FALLBACKS:
        fallback_fonts = {}
        for size in sizes:
            try:
                fallback_fonts[size] = ImageFont.truetype(font_path, size)
            except:
                fallback_fonts[size] = None
        fonts["fallbacks"].append(fallback_fonts)
    return fonts

fonts = load_fonts([30, 35, 40, 50])

def char_in_font(char, font):
    try:
        glyph = font.getmask(char)
        return glyph.getbbox() is not None
    except:
        return False

def smart_draw_text(draw, position, text, font_dict, size, fill):
    x, y = position
    primary_font = font_dict["primary"][size]
    fallbacks = font_dict["fallbacks"]

    for char in text:
        font_to_use = None
        if char_in_font(char, primary_font):
            font_to_use = primary_font
        else:
            for fb_fonts in fallbacks:
                fb_font = fb_fonts[size]
                if fb_font and char_in_font(char, fb_font):
                    font_to_use = fb_font
                    break
        if not font_to_use:
            font_to_use = primary_font

        draw.text((x, y), char, font=font_to_use, fill=fill)
        char_width = font_to_use.getbbox(char)[2] - font_to_use.getbbox(char)[0]
        x += char_width

def fetch_image(url, size=None):
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        img = Image.open(BytesIO(res.content)).convert("RGBA")
        if size:
            img = img.resize(size, Image.LANCZOS)
        return img
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None

@app.route('/bnr')
def generate_avatar_only():
    uid = request.args.get("uid")
    key = request.args.get("key")

    if key != SECRET_KEY:
        return "🚫 مفتاح غير صحيح", 403
    if not uid:
        return "يرجى تحديد UID", 400

    # جلب معلومات اللاعب من API الجديد
    try:
        api_url = f"https://info-plum-six.vercel.app/get?uid={uid}"
        res = requests.get(api_url, timeout=5)
        res.raise_for_status()
        data = res.json()

        # استخراج البيانات من الهيكل الجديد
        captain_info = data.get("captainBasicInfo", {})
        account_info = data.get("AccountInfo", {})
        
        # استخدام captainBasicInfo أولاً، ثم AccountInfo كبديل
        nickname = captain_info.get("nickname") or account_info.get("AccountName", "Unknown")
        likes = captain_info.get("liked") or account_info.get("AccountLikes", 0)
        level = captain_info.get("level") or account_info.get("AccountLevel", 0)
        avatar_id = captain_info.get("headPic") or account_info.get("AccountAvatarId")
        
        # إذا لم نجد avatar_id، نحاول من مصادر أخرى
        if not avatar_id:
            profile_info = data.get("AccountProfileInfo", {})
            # قد تكون الصورة في مكان آخر، نستخدم قيمة افتراضية
            avatar_id = 902000110  # قيمة افتراضية

        # استخدام uid من البيانات إذا كان متاحاً
        player_uid = captain_info.get("accountId") or uid

    except Exception as e:
        return f"❌ فشل في جلب البيانات: {e}", 500

    # تحميل صورة الخلفية
    bg_img = fetch_image("https://i.postimg.cc/L4PQBgmx/IMG-20250807-042134-670.jpg")
    if not bg_img:
        return "❌ فشل في تحميل الخلفية", 500

    img = bg_img.copy()
    draw = ImageDraw.Draw(img)

    # عرض الصورة الرمزية (Avatar)
    if avatar_id:
        avatar_img = fetch_image(
            f"https://pika-ffitmes-api.vercel.app/?item_id={avatar_id}&watermark=TaitanApi&key=PikaApis",
            AVATAR_SIZE
        )
        avatar_x, avatar_y = 90, 82
        if avatar_img:
            img.paste(avatar_img, (avatar_x, avatar_y), avatar_img)

    # رسم المستوى
    level_text = f"Lv. {level}"
    level_x = avatar_x - 40
    level_y = avatar_y + 160
    smart_draw_text(draw, (level_x, level_y), level_text, fonts, 50, "black")

    # رسم الاسم
    nickname_x = avatar_x + AVATAR_SIZE[0] + 80
    nickname_y = avatar_y - 3
    smart_draw_text(draw, (nickname_x, nickname_y), nickname, fonts, 50, "black")

    # رسم UID
    bbox_uid = fonts["primary"][35].getbbox(player_uid)
    text_w = bbox_uid[2] - bbox_uid[0]
    text_h = bbox_uid[3] - bbox_uid[1]
    img_w, img_h = img.size
    text_x = img_w - text_w - 110
    text_y = img_h - text_h - 17
    smart_draw_text(draw, (text_x, text_y), player_uid, fonts, 35, "white")

    # رسم عدد الإعجابات
    likes_text = f"{likes}"
    bbox_likes = fonts["primary"][40].getbbox(likes_text)
    likes_w = bbox_likes[2] - bbox_likes[0]
    likes_y = text_y - (bbox_likes[3] - bbox_likes[1]) - 25
    likes_x = img_w - likes_w - 60
    smart_draw_text(draw, (likes_x, likes_y), likes_text, fonts, 40, "black")

    # كتابة اسم المطور
    dev_text = "DEV BY : BNGX"
    bbox_dev = fonts["primary"][30].getbbox(dev_text)
    dev_w = bbox_dev[2] - bbox_dev[0]
    padding = 30
    dev_x = img_w - dev_w - padding
    dev_y = padding
    smart_draw_text(draw, (dev_x, dev_y), dev_text, fonts, 30, "white")

    # حفظ الصورة وإرسالها
    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return send_file(output, mimetype='image/png')

@app.route('/debug')
def debug():
    """واجهة لتصحيح الأخطاء"""
    uid = request.args.get("uid", "9747087237")
    
    try:
        api_url = f"https://info-eight-rho.vercel.app/get?uid={uid}"
        res = requests.get(api_url, timeout=5)
        res.raise_for_status()
        data = res.json()
        
        captain_info = data.get("captainBasicInfo", {})
        account_info = data.get("AccountInfo", {})
        
        return {
            "player_uid": uid,
            "captain_info_keys": list(captain_info.keys()) if captain_info else [],
            "account_info_keys": list(account_info.keys()) if account_info else [],
            "nickname": captain_info.get("nickname"),
            "liked": captain_info.get("liked"),
            "level": captain_info.get("level"),
            "headPic": captain_info.get("headPic"),
            "AccountName": account_info.get("AccountName"),
            "AccountLikes": account_info.get("AccountLikes"),
            "AccountLevel": account_info.get("AccountLevel"),
            "AccountAvatarId": account_info.get("AccountAvatarId")
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
