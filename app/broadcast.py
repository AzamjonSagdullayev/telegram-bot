"""
Broadcast Engine for AzamAI Business Bot.
Sends announcements to all registered customers asynchronously with rate limiting,
error handling, and campaign tracking.
"""
import asyncio
from datetime import datetime
from html import escape
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import Announcement, BroadcastCampaign, Customer

log = logging.getLogger(__name__)

# Mutex to prevent duplicate concurrent broadcasts
_broadcast_lock = asyncio.Lock()
_is_broadcasting = False


def is_broadcasting_active() -> bool:
    return _is_broadcasting


async def broadcast_announcement(
    bot: Bot,
    announcement_id: int | None = None,
    custom_title: str = "",
    custom_text: str = "",
    photo_file_id: str | None = None,
    admin_id: int | None = None,
) -> dict:
    """
    Broadcasts announcement to all registered customers.
    Returns summary dict with keys: total, success, failed, campaign_id.
    """
    global _is_broadcasting

    if _is_broadcasting:
        raise RuntimeError("A broadcast is already in progress. Please wait until it completes.")

    async with _broadcast_lock:
        _is_broadcasting = True
        try:
            # 1. Resolve content
            title = custom_title
            text = custom_text
            photo = photo_file_id

            if announcement_id:
                async with SessionLocal() as db:
                    ann = await db.get(Announcement, announcement_id)
                    if ann:
                        title = ann.title
                        text = ann.text
                        photo = ann.photo_file_id or photo
                        ann.is_published = True
                        ann.updated_at = datetime.now(ZoneInfo(settings.timezone))
                        await db.commit()

            # 2. Fetch distinct recipient telegram IDs
            async with SessionLocal() as db:
                recipients = (await db.scalars(select(Customer.telegram_id).distinct())).all()

            total = len(recipients)

            # 3. Create campaign record
            campaign = BroadcastCampaign(
                announcement_id=announcement_id,
                title=title,
                text=text,
                photo_file_id=photo,
                status="in_progress",
                total_recipients=total,
                successful_deliveries=0,
                failed_deliveries=0,
                started_at=datetime.now(ZoneInfo(settings.timezone)),
            )
            async with SessionLocal() as db:
                db.add(campaign)
                await db.commit()
                await db.refresh(campaign)
                campaign_id = campaign.id

            # 4. Format message text
            message_body = (
                f"📰 <b>{escape(title)}</b>\n\n"
                f"{escape(text)}"
            )

            success_count = 0
            failed_count = 0

            # 5. Broadcast loop with rate limiting (25 msg/sec)
            for tg_id in recipients:
                try:
                    if photo:
                        await bot.send_photo(
                            chat_id=tg_id,
                            photo=photo,
                            caption=message_body,
                            parse_mode="HTML",
                        )
                    else:
                        await bot.send_message(
                            chat_id=tg_id,
                            text=message_body,
                            parse_mode="HTML",
                        )
                    success_count += 1
                except TelegramRetryAfter as e:
                    log.warning("Flood limit reached. Sleeping for %s seconds", e.retry_after)
                    await asyncio.sleep(e.retry_after)
                    # Retry once
                    try:
                        if photo:
                            await bot.send_photo(
                                chat_id=tg_id,
                                photo=photo,
                                caption=message_body,
                                parse_mode="HTML",
                            )
                        else:
                            await bot.send_message(
                                chat_id=tg_id,
                                text=message_body,
                                parse_mode="HTML",
                            )
                        success_count += 1
                    except Exception as retry_err:
                        log.debug("Failed on retry to %s: %s", tg_id, retry_err)
                        failed_count += 1
                except (TelegramForbiddenError, TelegramBadRequest) as err:
                    # User blocked the bot or chat not found
                    log.debug("Cannot deliver to %s: %s", tg_id, err)
                    failed_count += 1
                except Exception as ex:
                    log.warning("Unexpected broadcast error for %s: %s", tg_id, ex)
                    failed_count += 1

                # Safe pacing: 40ms sleep (~25 messages/second)
                await asyncio.sleep(0.04)

            # 6. Update campaign completion
            async with SessionLocal() as db:
                c = await db.get(BroadcastCampaign, campaign_id)
                if c:
                    c.status = "completed"
                    c.successful_deliveries = success_count
                    c.failed_deliveries = failed_count
                    c.finished_at = datetime.now(ZoneInfo(settings.timezone))
                    await db.commit()

            result = {
                "campaign_id": campaign_id,
                "total": total,
                "success": success_count,
                "failed": failed_count,
                "title": title,
            }

            # 7. Notify initiating admin or all admins with report
            report_text = (
                "📢 <b>Xabar yuborish yakunlandi</b>\n\n"
                f"📌 <b>Mavzu:</b> {escape(title)}\n"
                f"👥 <b>Jami foydalanuvchilar:</b> {total}\n"
                f"✅ <b>Muvaffaqiyatli:</b> {success_count}\n"
                f"❌ <b>Yetkazilmadi:</b> {failed_count}"
            )
            if admin_id:
                try:
                    await bot.send_message(chat_id=admin_id, text=report_text, parse_mode="HTML")
                except Exception:
                    pass

            return result

        finally:
            _is_broadcasting = False
