import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
import asyncio

# Token del bot
API_TOKEN = 'TU_TOKEN_AQUI'

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Inicialización del bot y el dispatcher
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Opciones de conversión disponibles
conversion_options = {
    'pdf_to_word': {'source': 'pdf', 'target': 'docx'},
    'word_to_pdf': {'source': 'docx', 'target': 'pdf'}
}

# Definición de estados
class ConversionStates(StatesGroup):
    waiting_for_file = State()

# Función para realizar la conversión
def convert_file(file_path, conversion):
    base, _ = os.path.splitext(file_path)
    target_path = ""
    try:
        if conversion == 'word_to_pdf':
            subprocess.run(['unoconv', '-f', 'pdf', file_path], check=True)
            target_path = base + '.pdf'
        elif conversion == 'pdf_to_word':
            target_path = base + '.docx'
            subprocess.run(['pdf2docx', file_path, target_path], check=True)
        return target_path
    except subprocess.CalledProcessError:
        return None

# Comando /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="PDF a Word", callback_data="pdf_to_word")],
        [InlineKeyboardButton(text="Word a PDF", callback_data="word_to_pdf")]
    ])
    await message.answer("¡Bienvenido! Selecciona la conversión que deseas realizar:", reply_markup=markup)

# Manejo de la opción seleccionada
@dp.callback_query(lambda c: c.data in conversion_options)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    conversion = callback_query.data
    await state.update_data(conversion=conversion)
    await state.set_state(ConversionStates.waiting_for_file)
    await bot.send_message(callback_query.from_user.id, f"Has seleccionado {conversion}. Envía el archivo para convertir.")
    await bot.answer_callback_query(callback_query.id)

# Manejo de archivos
@dp.message(ConversionStates.waiting_for_file, content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conversion = data.get('conversion')
    document = message.document
    file_info = await bot.get_file(document.file_id)
    file_path = file_info.file_path
    downloaded_file = await bot.download_file(file_path)

    local_filename = document.file_name
    with open(local_filename, 'wb') as f:
        f.write(downloaded_file.read())

    await message.answer("Archivo recibido. Procesando conversión...")
    result_path = convert_file(local_filename, conversion)

    if result_path and os.path.exists(result_path):
        await message.answer_document(types.FSInputFile(result_path))
        os.remove(local_filename)
        os.remove(result_path)
    else:
        await message.answer("Error durante la conversión.")

    await state.clear()

# Ejecución del bot
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
