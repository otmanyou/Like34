import logging
import nest_asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters
import requests
import asyncio
from bs4 import BeautifulSoup

# تطبيق nest_asyncio
nest_asyncio.apply()

# إعدادات البوت
BOT_TOKEN = "7500067602:AAFA-Cwv3w_B2_Ayg0fcN0fCOXG717n_DLA"
CHANNEL_ID = -1002349706113
CHANNEL_LINK = "https://t.me/l7aj_ff_group"

# قائمة المناطق
REGIONS = {
    "ind": {"name": "India"},
    "sg": [{"name": "Bangladesh"}, {"name": "Europe"}, {"name": "Middle East & Africa"}],
    "us": [{"name": "North America"}, {"name": "South America - Spanish"}],
}

# تفعيل الـ logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تخزين اللغات لكل مستخدم
user_languages = {}

# دالة استخراج النتيجة من HTML
def extract_result_text(response_text):
    soup = BeautifulSoup(response_text, 'html.parser')
    result_div = soup.find('div', class_='result')
    return result_div.get_text(strip=True) if result_div else None

# وظيفة إرسال الطلبات إلى الخادم
def send_request(uid, region):
    url = f'https://tools.freefireinfo.in/like.php?success=1'
    data = {'uid': uid, 'region': region}

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return extract_result_text(response.text)
    except requests.exceptions.RequestException:
        return None

# وظيفة تنفيذ طلبات الإعجابات
async def claim_likes(uid, update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_language = user_languages.get(user_id, "ar")

    if not uid.isnumeric():
        await update.message.reply_text("❌ خطأ: يجب إدخال UID صالح." if user_language == "ar" else "❌ Error: Please enter a valid UID.")
        return

    message = await update.message.reply_text("⏳ جاري التحقق..." if user_language == "ar" else "⏳ Checking...")

    for region, data in REGIONS.items():
        if isinstance(data, list):
            for _ in data:
                result = send_request(uid, region)
                if result:
                    await message.delete()
                    await update.message.reply_text(result)
                    return
        else:
            result = send_request(uid, region)
            if result:
                await message.delete()
                await update.message.reply_text(result)
                return

    await message.edit_text("❌ لم يتم العثور على خادم متاح." if user_language == "ar" else "❌ No available server found.")

# وظيفة بدء البوت مع اختيار اللغة (تعمل فقط في المجموعة)
async def start(update: Update, context: CallbackContext):
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text(f"🚨 البوت يعمل فقط في المجموعة:\n{CHANNEL_LINK}")
        return

    keyboard = [[InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar"),
                 InlineKeyboardButton("English 🇬🇧", callback_data="lang_en")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌍 اختر لغتك / Choose your language:", reply_markup=reply_markup)

# معالجة اختيار اللغة
async def select_language(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_lang = query.data.split("_")[1]  # الحصول على اللغة من callback_data
    
    # تحديث اللغة
    user_languages[user_id] = user_lang
    
    # إرسال الرسالة في الخاص
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "⚠️ مرحبا بك في بوت L7 LIST FF! ⚠️\n\n"
                "🚨 البوت يعمل فقط في هذه المجموعة:\n"
                f"🔗 {CHANNEL_LINK}\n\n"
                "✅ الآن يمكنك استخدام الأمر /like في المجموعة!"
                if user_lang == "ar" 
                else 
                "⚠️ Welcome to L7 LIST FF bot! ⚠️\n\n"
                "🚨 The bot only works in this group:\n"
                f"🔗 {CHANNEL_LINK}\n\n"
                "✅ Now you can use /like command in the group!"
            )
        )
    except Exception as e:
        logger.error(f"فشل إرسال الرسالة في الخاص: {e}")
        await query.message.reply_text("❌ يرجى بدء محادثة مع البوت أولاً!")

    # حذف رسالة الاختيار في المجموعة
    await query.message.delete()

# تنفيذ أمر /like فقط داخل المجموعة
async def like_command(update: Update, context: CallbackContext):
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text(f"🚨 البوت يعمل فقط في المجموعة:\n{CHANNEL_LINK}")
        return

    user_id = update.message.from_user.id
    user_language = user_languages.get(user_id, "ar")

    message_text = update.message.text.strip()
    match = re.match(r"/like (\d+)", message_text)
    
    if match:
        uid = match.group(1)
        await claim_likes(uid, update, context)
    else:
        await update.message.reply_text(
            "❌ خطأ: استخدم الصيغة الصحيحة:\n/like 987288316"
            if user_language == "ar"
            else "❌ Error: Use the correct format:\n/like 987288316"
        )

# تجاهل أي رسائل أخرى في الخاص
async def handle_private_message(update: Update, context: CallbackContext):
    if update.message.chat.type == "private":
        await update.message.reply_text(f"🚨 البوت يعمل فقط في المجموعة:\n{CHANNEL_LINK}")

# الوظيفة الرئيسية
async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # handlers للمجموعة فقط
    group_filter = filters.ChatType.GROUP | filters.ChatType.SUPERGROUP
    application.add_handler(CommandHandler("start", start, group_filter))
    application.add_handler(CommandHandler("like", like_command, group_filter))
    
    # handlers للخاص
    private_filter = filters.ChatType.PRIVATE
    application.add_handler(MessageHandler(private_filter & filters.TEXT, handle_private_message))
    
    # handler لاختيار اللغة
    application.add_handler(CallbackQueryHandler(select_language))

    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())