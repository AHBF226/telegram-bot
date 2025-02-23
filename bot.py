import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
import asyncio

# Token del bot
API_TOKEN = 'TU_TOKEN_AQUI'

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Inicialización del bot y dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Opciones de conversión
conversion_options = {
    'pdf_to_word': {'source': 'pdf', 'target': 'docx'},
    'word_to_pdf': {'source': 'docx', 'target': 'pdf'},
}

# Definición de estados
class ConversionStates(StatesGroup):
    waiting_for_file = State()

# Teclado de opciones
async def conversion_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="PDF a Word", callback_data="pdf_to_word")],
        [InlineKeyboardButton(text="Word a PDF", callback_data="word_to_pdf")]
    ])
    return keyboard

# Comando /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    keyboard = await conversion_keyboard()
    await message.answer("¡Hola! Selecciona el tipo de conversión:", reply_markup=keyboard)

# Callback para conversión
@dp.callback_query(lambda c: c.data in conversion_options)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    conversion = callback_query.data
    await state.update_data(conversion=conversion)
    await state.set_state(ConversionStates.waiting_for_file)
    await callback_query.message.answer(f"Has seleccionado: {conversion.replace('_', ' ').title()}. Envía el archivo para continuar.")
    await bot.answer_callback_query(callback_query.id)

# Conversión de archivos
def convert_file(file_path, conversion):
    base, _ = os.path.splitext(file_path)
    target_path = f"{base}.{conversion_options[conversion]['target']}"
    try:
        if conversion == 'word_to_pdf':
            subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', file_path], check=True)
        elif conversion == 'pdf_to_word':
            subprocess.run(['pdf2docx', file_path, target_path], check=True)
        return target_path if os.path.exists(target_path) else None
    except Exception as e:
        logging.error(f"Error durante la conversión: {e}")
        return None

# Recepción del archivo
@dp.message(ConversionStates.waiting_for_file, content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conversion = data.get('conversion')
    document = message.document

    file_path = f"downloads/{document.file_name}"
    os.makedirs("downloads", exist_ok=True)

    # Descargar archivo
    await bot.download(document, destination=file_path)

    await message.answer("Archivo recibido, procesando...")

    # Realizar conversión
    result_path = convert_file(file_path, conversion)

    if result_path:
        await message.answer_document(FSInputFile(result_path))
        os.remove(file_path)
        os.remove(result_path)
    else:
        await message.answer("❌ Error en la conversión.")

    await state.clear()

# Ejecución del bot
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
