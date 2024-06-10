import os
from telegram import Update,PhotoSize
from telegram.ext import Application,CommandHandler,MessageHandler,filters,ContextTypes,ConversationHandler
import google.generativeai as genai
from PIL import Image
import logging
import io
from dotenv import load_dotenv

load_dotenv()

#Username and Token of Your Telegram Bot
Token = "Your Telegram Token"
username = "Your Bot username"

#Configure Gemini api key
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))



logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WAITING_FOR_PROMPT = 1

async def start_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'''Hey!  @{update.message.chat.username} Ask any question or generate code''')

async def help_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '''Hi! Welcome to @example_bot \nTHE BOT IS FREE TO USE \n
The bot can assist you with any problem and can write code for you \n
You can get a description of an image \n
For Question answering just write your question here and you will get the answer \n
For Code Generation type    "/generate_code Write python code for calculator"''')

async def image_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Send any image to generate descriptions or identifying objects in images')
    await update.message.reply_text('Please send the image first, then send a message starting with "Image:" followed by your prompt.')
    return WAITING_FOR_PROMPT

async def code_generation(update:Update,context:ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Generating Code")
        text = update.message.text
        text = text.replace("/generate_code","")
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content(update.message.text)
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Error handling image: {e}")
        await update.message.reply_text("An error occurred while processing the image. Please try again.")



async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: str = update.message.text

    print(f'user ({update.message.chat.id}) in {update.message.chat.type}:"{text}"')

    with open("user.txt", 'a') as file:
        file.write(f'{update.message.chat.username} -- {text}\n')

    if any(greeting in text.lower().startswith(greeting) for greeting in ["hi", "hello", "hey"]):
        await update.message.reply_text("Hi there! I'm example_bot. What can I do for you today?")
    else:
        await handle_text_message(update, text)


# Image Handler
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo: PhotoSize = update.message.photo[-1]  # Get the highest resolution photo
        file = await photo.get_file()
        file_content = await file.download_as_bytearray()

        # Load the image using Pillow
        image = Image.open(io.BytesIO(file_content))

        # Save image content in context for later use
        context.user_data['image'] = image

        await update.message.reply_text('Image received. Now send the prompt starting with "Image:".')
        return WAITING_FOR_PROMPT
    except Exception as e:
        logger.error(f"Error handling image: {e}")
        await update.message.reply_text("An error occurred while processing the image. Please try again.")

#Image Prompt Handler
async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        image = context.user_data.get('image')
        if not image:
            await update.message.reply_text("Please send the image first.")
            return WAITING_FOR_PROMPT

        text = update.message.text
        if not text.startswith("Image:"):
            await update.message.reply_text('Please start your prompt with "Image:".')
            return WAITING_FOR_PROMPT

        prompt = text.replace("Image:", "").strip()

        # Configure and generate content
        model = genai.GenerativeModel('gemini-pro-vision')
        response = model.generate_content([prompt, image], stream=True)
        response.resolve()
        print(response.text)
        await update.message.reply_text("Processing Image")
        await update.message.reply_text(response.text)

        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error processing prompt: {e}")
        await update.message.reply_text("An error occurred while processing the prompt. Please try again.")
        return ConversationHandler.END

# Text Handler
async def handle_text_message(update: Update, text: str):
    try:
        await update.message.reply_text("Generating Response")
        logger.info(f'user ({update.message.chat.id}) in {update.message.chat.type}:"{text}"')

        # generate content
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(text)

        # Clean response text
        response_text = response.text.replace("#", "").replace("*", "")
        print(response_text)
        await update.message.reply_text(response_text)
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        await update.message.reply_text("An error occurred while generating the response. Please try again.")


async def error(update:Update,context:ContextTypes.DEFAULT_TYPE):
    logger.warning(f'Update {update} caused error {context.error}')


if __name__ =="__main__":
    print("Starting bot.....")
    app = Application.builder().token(Token).build()

    #Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('image', image_command))
    app.add_handler(CommandHandler('generate_code', code_generation))

    #Messages
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, handle_image)],
        states={
            WAITING_FOR_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt)],
        },
        fallbacks=[],
    )
    app.add_handler(conv_handler)

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.add_error_handler(error)

    app.run_polling(poll_interval=2)
