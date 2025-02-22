import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Token del bot (reemplaza 'TU_TOKEN_DE_TELEGRAM' con el token real)
API_TOKEN = 'AAEUN8DkISMIfTFKnNaLGhWnTy6bHU3YWKE'

# Configuración básica y almacenamiento de estados
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# Opciones de conversión disponibles
conversion_options = {
    'pdf_to_word': {'source': 'pdf', 'target': 'docx'},
    'word_to_pdf': {'source': 'docx', 'target': 'pdf'},
    # Puedes agregar más conversiones aquí
}

# Definición de estados con FSM
class ConversionStates(StatesGroup):
    waiting_for_file = State()

# Función que se encarga de realizar la conversión
def convert_file(file_path, conversion):
    base, _ = os.path.splitext(file_path)
    target_path = ""
    try:
        if conversion == 'word_to_pdf':
            # Usamos unoconv para convertir de Word a PDF
            subprocess.run(['unoconv', '-f', 'pdf', file_path], check=True)
            target_path = base + '.pdf'
        elif conversion == 'pdf_to_word':
            # Usamos pdf2docx para convertir de PDF a Word
            target_path = base + '.docx'
            subprocess.run(['pdf2docx', file_path, target_path], check=True)
        # Se pueden agregar más condiciones para otros formatos
        return target_path
    except subprocess.CalledProcessError:
        return None

# Handler para el comando /start que muestra el menú de conversión
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("PDF a Word", callback_data="pdf_to_word"),
        types.InlineKeyboardButton("Word a PDF", callback_data="word_to_pdf")
    )
    await message.answer("¡Bienvenido! Selecciona la conversión que deseas realizar:", reply_markup=markup)

# Handler para los botones interactivos del menú
@dp.callback_query_handler(lambda c: c.data in conversion_options)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    conversion = callback_query.data
    # Guardamos la opción seleccionada en el estado del usuario
    await state.update_data(conversion=conversion)
    await ConversionStates.waiting_for_file.set()
    await bot.send_message(callback_query.from_user.id, f"Has seleccionado {conversion}. Ahora envía el archivo para convertirlo.")
    await bot.answer_callback_query(callback_query.id)

# Handler para recibir el archivo del usuario y procesar la conversión
@dp.message_handler(state=ConversionStates.waiting_for_file, content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conversion = data.get('conversion')
    document = message.document
    file_info = await bot.get_file(document.file_id)
    file_path = file_info.file_path
    downloaded_file = await bot.download_file(file_path)
    local_filename = document.file_name

    # Guardamos el archivo en el servidor
    with open(local_filename, 'wb') as f:
        f.write(downloaded_file.read())

    await message.answer("Archivo recibido, procesando conversión...")

    # Realizamos la conversión
    result_path = convert_file(local_filename, conversion)

    if result_path and os.path.exists(result_path):
        await message.answer_document(types.InputFile(result_path))
        # Eliminamos los archivos temporales
        os.remove(local_filename)
        os.remove(result_path)
    else:
        await message.answer("Error durante la conversión.")

    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
