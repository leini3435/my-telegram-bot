from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, filters
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
GROUP_CHAT_ID = --1003736967957          # 你的群组ID
ADMIN_USER_ID = 1861060591              # 你的Telegram user ID（用于限制命令）

AD_INTERVAL_SECONDS = 1800              # 每30分钟发一次

ADVERTS = [  # ↑ 上面定义的广告列表
    # ... 粘贴上面的 ADVERTS 内容
]

# ==================== 轮播核心函数 ====================
async def send_next_ad(context: ContextTypes.DEFAULT_TYPE):
    chat_id = GROUP_CHAT_ID
    index_key = f"ad_index_{chat_id}"

    current_index = context.bot_data.get(index_key, 0)
    ad = ADVERTS[current_index % len(ADVERTS)]  # 防止越界

    # 构建按钮
    keyboard = []
    for btn_text, btn_value in ad["buttons"]:
        if btn_value.startswith("http"):
            keyboard.append([InlineKeyboardButton(btn_text, url=btn_value)])
        else:
            # 如果是 callback_data，可以后续处理点击事件
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=btn_value)])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=ad["photo"],                    # 支持 URL 或文件对象 open("path", "rb")
            caption=ad.get("caption", ""),
            parse_mode=ad.get("parse_mode", None),
            reply_markup=reply_markup,
            disable_notification=True,            # 可选：静默发送
        )
        logging.info(f"广告发送成功 #{current_index}: {ad['caption'][:50]}...")
    except Exception as e:
        logging.error(f"发送广告失败: {e}")

    # 更新索引（循环）
    next_index = (current_index + 1) % len(ADVERTS)
    context.bot_data[index_key] = next_index


# ==================== 管理员命令 ====================
async def start_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("无权限")
        return

    chat_id = GROUP_CHAT_ID
    job_name = f"ad_rotation_{chat_id}"

    if context.job_queue.get_jobs_by_name(job_name):
        await update.message.reply_text("轮播已在运行")
        return

    context.job_queue.run_repeating(
        callback=send_next_ad,
        interval=AD_INTERVAL_SECONDS,
        first=5,                        # 启动后5秒发第一条（可改0立即发）
        name=job_name,
        chat_id=chat_id,
    )

    await update.message.reply_text(
        f"图片+按钮广告轮播已启动！\n间隔：{AD_INTERVAL_SECONDS//60}分钟，共 {len(ADVERTS)} 条循环。"
    )


async def stop_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    job_name = f"ad_rotation_{GROUP_CHAT_ID}"
    jobs = context.job_queue.get_jobs_by_name(job_name)

    if not jobs:
        await update.message.reply_text("没有正在运行的轮播")
        return

    for job in jobs:
        job.schedule_removal()

    context.bot_data.pop(f"ad_index_{GROUP_CHAT_ID}", None)
    await update.message.reply_text("广告轮播已停止")


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    app = Application.builder().token(TOKEN).build()

    ap# 只允許 admin 使用這些命令（你的 ADMIN_USER_ID）
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_USER_ID:
            await update.message.reply_text("只有管理員能用這個命令！")
            return
        return await func(update, context)
    return wrapper

@admin_only
async def add_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "用法: /add_ad 圖片URL 文字 [按鈕文字|連結] [按鈕文字|連結] ...\n"
            "例: /add_ad https://i.imgur.com/xxx.jpg 限時 ¥99 買|https://link.com 詳情|https://info.com"
        )
        return

    photo = context.args[0]
    caption = context.args[1]
    buttons = []
    for arg in context.args[2:]:
        if '|' in arg:
            text, url = arg.split('|', 1)
            buttons.append([InlineKeyboardButton(text.strip(), url=url.strip())])

    ad = {
        "photo": photo,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": InlineKeyboardMarkup(buttons) if buttons else None
    }

    # 存到 bot_data（全局列表）
    if 'ads_list' not in context.application.bot_data:
        context.application.bot_data['ads_list'] = []
    context.application.bot_data['ads_list'].append(ad)

    await update.message.reply_text(f"已添加第 {len(context.application.bot_data['ads_list'])} 條廣告！")

@admin_only
async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ads = context.application.bot_data.get('ads_list', [])
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
        ads = context.application.bot_data.get('ads_list', [])
        if 0 <= index < len(ads):
            removed = ads.pop(index)
            context.application.bot_data['ads_list'] = ads
            await update.message.reply_text(f"已刪除第 {index+1} 條: {removed['caption'][:30]}...")
        else:
            await update.message.reply_text("編號無效！")
    except ValueError:
        await update.message.reply_text("編號必須是數字！")

@admin_only
async def clear_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.application.bot_data['ads_list'] = []
    await update.message.reply_text("所有廣告已清空！")

# 修改原 send_next_ad 函數，用動態列表
async def send_next_ad(context: ContextTypes.DEFAULT_TYPE):
    chat_id = GROUP_CHAT_ID
    index_key = f"ad_index_{chat_id}"
    current_index = context.bot_data.get(index_key, 0)

    ads = context.application.bot_data.get('ads_list', [])
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
        )
        logging.info(f"發送廣告 #{current_index + 1}")
    except Exception as e:
        logging.error(f"發送失敗: {e}")

    next_index = (current_index + 1) % len(ads)
    context.bot_data[index_key] = next_indexp.add_handler(CommandHandler("start_ads", start_ads))
    app.add_handler(CommandHandler("stop_ads", stop_ads))
app.add_handler(CommandHandler("add_ad", add_ad))
app.add_handler(CommandHandler("list_ads", list_ads))
app.add_handler(CommandHandler("del_ad", del_ad))
app.add_handler(CommandHandler("clear_ads", clear_ads))
    print("机器人启动...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
