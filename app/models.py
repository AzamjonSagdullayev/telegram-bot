from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, Integer, String, Text, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ServiceOrder(Base):
    __tablename__ = "service_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50))
    service_id: Mapped[str] = mapped_column(String(100), default="")
    service_name: Mapped[str] = mapped_column(String(255), default="")
    service_price: Mapped[str] = mapped_column(String(100), default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(String(50), default="yangi")  # yangi, qabul_qilindi, rad_etildi
    handled_by_admin: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Announcement(Base):
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BroadcastCampaign(Base):
    __tablename__ = "broadcast_campaigns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    announcement_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="in_progress")  # in_progress, completed, failed
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    successful_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    failed_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BusinessLocation(Base):
    __tablename__ = "business_locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    address: Mapped[str] = mapped_column(Text, default="")
    landmark: Mapped[str] = mapped_column(String(255), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    google_maps_url: Mapped[str] = mapped_column(String(500), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyReportLog(Base):
    __tablename__ = "daily_report_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_date: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # YYYY-MM-DD
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    recipients_count: Mapped[int] = mapped_column(Integer, default=0)
    summary_text: Mapped[str] = mapped_column(Text, default="")


class AdminAction(Base):
    __tablename__ = "admin_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action_type: Mapped[str] = mapped_column(String(100))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
