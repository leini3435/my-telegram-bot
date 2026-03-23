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

    app.add_handler(CommandHandler("start_ads", start_ads))
    app.add_handler(CommandHandler("stop_ads", stop_ads))

    print("机器人启动...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()