import logging
import json
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = '7591671940:AAGEBw61CqZRFOyPY59pVqlJ-mIkUtZqPfI' 
JSON_FILE = 'Bot de bienvenida.json'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CARGA DEL FLUJO DEL CHATBOT ---
def load_chatbot_flow(file_path: str) -> dict:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            flow_string = data['model']['text']
            return json.loads(flow_string)
    except Exception as e:
        logger.error(f"Error cargando o parseando el JSON: {e}")
        return None

# --- VARIABLES GLOBALES ---
CHATBOT_FLOW = load_chatbot_flow(JSON_FILE)
user_states = {}

# --- FUNCIONES DEL BOT ---

async def send_step_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, step_id: str):
    step_data = CHATBOT_FLOW.get(step_id)
    if not step_data:
        logger.warning(f"No se encontró el step_id '{step_id}' en el JSON.")
        return
    try:
        message_params = step_data['question'][0]['params']
        text = message_params.get('text', 'Mensaje no encontrado.')
        keyboard = []
        if 'buttons' in message_params:
            for button_info in message_params['buttons']:
                button_text = button_info['text']
                if button_info['type'] == 'inline':
                     keyboard.append([InlineKeyboardButton(button_text, callback_data=button_text)])
                elif button_info['type'] == 'url':
                     keyboard.append([InlineKeyboardButton(button_text, url=button_info['url'])])
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    except (KeyError, IndexError) as e:
        logger.error(f"Error de estructura en el JSON para el step '{step_id}': {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"Nuevo usuario {chat_id} ha iniciado la conversación con /start.")
    initial_step = "0"
    user_states[chat_id] = initial_step
    await send_step_message(context, chat_id, initial_step)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    chat_id = query.message.chat_id
    callback_data = query.data
    
    print("\n--- ¡ÉXITO! EL button_handler SE EJECUTÓ ---")
    print(f"Callback data: '{callback_data}'")

    current_step_id = user_states.get(chat_id)
    if not current_step_id:
        print("Error: No se encontró estado para el usuario.")
        return
        
    current_step_data = CHATBOT_FLOW.get(current_step_id)
    next_step_id = None
    if 'answer' in current_step_data:
        for option in current_step_data['answer'][0]['params']:
            if option.get('value') == callback_data:
                next_step_id = option['params'][0]['params']['step']
                break
            elif option.get('type') == 'else':
                # Aseguramos que el 'else' también tenga la estructura correcta.
                try:
                    next_step_id = option['params'][0]['params']['step']
                except (KeyError, IndexError):
                    next_step_id = None # Si el 'else' está malformado, no hacemos nada.
    
    if next_step_id is not None:
        next_step_id_str = str(next_step_id)
        user_states[chat_id] = next_step_id_str
        print(f"Transición al paso: {next_step_id_str}")
        await send_step_message(context, chat_id, next_step_id_str)
    else:
        print(f"No se encontró un siguiente paso para la data '{callback_data}' en el paso '{current_step_id}'")

def main():
    if not CHATBOT_FLOW:
        logger.error("No se pudo cargar el flujo del bot. El bot no se iniciará.")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("El bot se está iniciando...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
