import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    filters,
)

# ==================== 配置 ====================
TOKEN = "8732531903:AAFbxHAKCVND1s7XuXfl2hUi2nqCa6barBk"
GROUP_CHAT_ID = -1003736967957  # 注意：只有一個負號
ADMIN_USER_ID = 1861060591      # 你的 ID
AD_INTERVAL_SECONDS = 1800      # 每30分鐘

# ==================== 管理員命令限制裝飾器 ====================
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_USER_ID:
            await update.message.reply_text("只有管理員能用這個命令！")
            return
        return await func(update, context)
    return wrapper

# ==================== 動態廣告管理命令 ====================
@admin_only
async def add_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "用法: /add_ad 圖片URL 文字 [按鈕文字|連結] [按鈕文字|連結] ...\n"
            "例: /add_ad https://i.imgur.com/xxx.jpg 限時 ¥99 買|https://link.com 詳情|https://info.com"
        )
        return

    photo = context.args[0]
    caption = ' '.join(context.args[1:]) if len(context.args) > 2 else context.args[1]  # 支援多詞 caption
    buttons = []
    # 從最後參數開始解析按鈕（假設 caption 後都是按鈕）
    button_args_start = 2 if len(context.args) > 2 else len(context.args)
    for arg in context.args[button_args_start:]:
        if '|' in arg:
            text, url = arg.split('|', 1)
            buttons.append([InlineKeyboardButton(text.strip(), url=url.strip())])

    ad = {
        "photo": photo,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": InlineKeyboardMarkup(buttons) if buttons else None
    }

    if 'ads_list' not in context.bot_data:
        context.bot_data['ads_list'] = []
    context.bot_data['ads_list'].append(ad)
    await update.message.reply_text(f"已添加第 {len(context.bot_data['ads_list'])} 條廣告！")


@admin_only
async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ads = context.bot_data.get('ads_list', [])
    if not ads:
        await update.message.reply_text("目前沒有廣告。")
        return

    text = "當前廣告列表：\n"
    for i, ad in enumerate(ads, 1):
        text += f"{i}. 文字: {ad['caption'][:50]}... 圖片: {ad['photo']}\n"
        if ad.get('reply_markup'):
            text += "   有按鈕\n"
    await update.message.reply_text(text)


@admin_only
async def del_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法: /del_ad 編號  (從 /list_ads 看編號)")
        return
    try:
        index = int(context.args[0]) - 1
        ads = context.bot_data.get('ads_list', [])
        if 0 <= index < len(ads):
            removed = ads.pop(index)
            context.bot_data['ads_list'] = ads
            await update.message.reply_text(f"已刪除第 {index+1} 條: {removed['caption'][:30]}...")
        else:
            await update.message.reply_text("編號無效！")
    except ValueError:
        await update.message.reply_text("編號必須是數字！")


@admin_only
async def clear_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data['ads_list'] = []
    await update.message.reply_text("所有廣告已清空！")

# ==================== 輪播發送函數（使用動態列表） ====================
async def send_next_ad(context: ContextTypes.DEFAULT_TYPE):
    chat_id = GROUP_CHAT_ID
    index_key = f"ad_index_{chat_id}"
    current_index = context.bot_data.get(index_key, 0)

    ads = context.bot_data.get('ads_list', [])
    if not ads:
        logging.info("無廣告可發，跳過。")
        return

    ad = ads[current_index % len(ads)]

    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=ad["photo"],
            caption=ad.get("caption", ""),
            parse_mode=ad.get("parse_mode"),
            reply_markup=ad.get("reply_markup"),
            disable_notification=True,
        )
        logging.info(f"發送廣告 #{current_index + 1}")
    except Exception as e:
        logging.error(f"發送失敗: {e}")

    next_index = (current_index + 1) % len(ads)
    context.bot_data[index_key] = next_index

# ==================== 啟動/停止輪播 ====================
async def start_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("無權限")
        return

    chat_id = GROUP_CHAT_ID
    job_name = f"ad_rotation_{chat_id}"

    if context.job_queue.get_jobs_by_name(job_name):
        await update.message.reply_text("輪播已在運行")
        return

    context.job_queue.run_repeating(
        callback=send_next_ad,
        interval=AD_INTERVAL_SECONDS,
        first=5,
        name=job_name,
        chat_id=chat_id,
    )
    ads_count = len(context.bot_data.get('ads_list', []))
    await update.message.reply_text(
        f"圖片+按鈕廣告輪播已啟動！\n間隔：{AD_INTERVAL_SECONDS//60}分鐘，共 {ads_count} 條循環。"
    )


async def stop_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    job_name = f"ad_rotation_{GROUP_CHAT_ID}"
    jobs = context.job_queue.get_jobs_by_name(job_name)
    if not jobs:
        await update.message.reply_text("沒有正在運行的輪播")
        return

    for job in jobs:
        job.schedule_removal()

    context.bot_data.pop(f"ad_index_{GROUP_CHAT_ID}", None)
    await update.message.reply_text("廣告輪播已停止")


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    app = Application.builder().token(TOKEN).build()

    # 添加所有 handler
    app.add_handler(CommandHandler("start_ads", start_ads))
    app.add_handler(CommandHandler("stop_ads", stop_ads))
    app.add_handler(CommandHandler("add_ad", add_ad))
    app.add_handler(CommandHandler("list_ads", list_ads))
    app.add_handler(CommandHandler("del_ad", del_ad))
    app.add_handler(CommandHandler("clear_ads", clear_ads))

    print("機器人啟動中...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
