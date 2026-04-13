# 🔔 Bot Nhắc Việc Telegram

Bot Telegram giúp quản lý và nhắc nhở công việc hàng ngày.

## ✨ Tính năng

- **Thêm việc** nhanh — gõ thẳng hoặc dùng `/add`
- **Nút bấm ✅** để đánh dấu hoàn thành
- **Nhắc nhở tự động** vào 8h sáng và 8h tối
- **Deadline** — thêm hạn cho từng việc
- **Xóa / Dọn dẹp** việc đã xong

## 🚀 Cài đặt

### Bước 1: Tạo bot trên Telegram
1. Mở Telegram, tìm **@BotFather**
2. Gõ `/newbot`, đặt tên và username cho bot
3. Copy **token** mà BotFather gửi cho bạn

### Bước 2: Cài thư viện
```bash
pip install python-telegram-bot==20.7
```

### Bước 3: Cấu hình
Mở file `telegram_reminder_bot.py`, tìm dòng:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
```
Thay bằng token của bạn:
```python
BOT_TOKEN = "1234567890:ABCdefGhIjKlMnOpQrStUvWxYz"
```

### Bước 4: Chạy bot
```bash
python telegram_reminder_bot.py
```

## 📌 Các lệnh

| Lệnh | Mô tả |
|-------|--------|
| `/start` | Bắt đầu sử dụng bot |
| `/add <tên việc>` | Thêm việc mới |
| `/add Họp team \| 2025-04-15` | Thêm việc có deadline |
| `/list` | Xem tất cả công việc |
| `/done` | Hiện nút bấm để đánh dấu xong |
| `/delete` | Hiện nút bấm để xóa việc |
| `/clear` | Xóa tất cả việc đã hoàn thành |
| `/remind` | Nhận nhắc nhở ngay |
| `/help` | Xem hướng dẫn |

**💡 Mẹo:** Gõ thẳng tên việc (không cần `/add`) cũng tự thêm!

## ⏰ Nhắc nhở tự động

Bot tự gửi nhắc nhở vào **8:00 sáng** và **20:00 tối** mỗi ngày.

Muốn đổi giờ? Sửa trong file bot:
```python
REMINDER_TIMES = ["08:00", "20:00"]
```

## 📁 Dữ liệu

Tất cả công việc được lưu trong file `tasks_data.json` cùng thư mục với bot.
