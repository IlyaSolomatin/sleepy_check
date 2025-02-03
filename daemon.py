import asyncio
import os
from http import HTTPStatus
from google.cloud import firestore
import datetime
import matplotlib.pyplot as plt
import io
import pandas as pd

import uvicorn
from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, request

from telegram import Update, MenuButtonCommands, BotCommand, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    filters,
    MessageHandler
)

URL = os.getenv("URL")
PORT = int(os.getenv("PORT", "8080"))  
TOKEN = os.getenv("TOKEN")

project_id = 'dynamic-now-724'
database = 'sleepy'
data_collection = 'records'
db = firestore.Client(project=project_id, database=database)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_html(
        text="Hey",
        protect_content=True,
        reply_markup=ReplyKeyboardRemove()
    )

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        score = float(update.message.text)
        if 1 <= score <= 10:
            doc_ref = db.collection(data_collection).document()
            doc_ref.set({
                'user_id': update.effective_user.id,
                'timestamp': datetime.datetime.now(),
                'score': score
            })
            await update.message.reply_text("Got you")
        else:
            await update.message.reply_text("You dumb?")
    except ValueError:
        await update.message.reply_text("You dumb?")


async def report(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    docs = db.collection(data_collection).where('user_id', '==', user_id).stream()
    
    records = []
    for doc in docs:
        records.append(doc.to_dict())
    
    df = pd.DataFrame(records)
    if df.empty:
        await update.message.reply_text("No data available")
        return
        
    df['hour'] = df['timestamp'].dt.hour
    hourly_avg = df.groupby('hour')['score'].mean()
    
    plt.figure(figsize=(10, 6))
    plt.plot(hourly_avg.index, hourly_avg.values, marker='o')
    plt.xlabel('Hour')
    plt.ylabel('Average Score')
    plt.grid(True)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    await update.message.reply_photo(buf)

async def main():
    context_types = ContextTypes(context=CallbackContext)
    application = (
        Application.builder().token(TOKEN).updater(None).context_types(context_types).build()
    )

    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("report", "Get the report of your typical sleepiness")
    ])

    private_chat_filter = filters.ChatType.PRIVATE

    application.add_handler(CommandHandler("start", start, filters=private_chat_filter))
    application.add_handler(CommandHandler("report", report, filters=private_chat_filter))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & private_chat_filter, handle_message))

    await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.MESSAGE)

    flask_app = Flask(__name__)

    @flask_app.post("/telegram")  
    async def telegram() -> Response:
        await application.update_queue.put(Update.de_json(data=request.json, bot=application.bot))
        return Response(status=HTTPStatus.OK)

    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=WsgiToAsgi(flask_app),
            port=PORT,
            use_colors=False,
            host="0.0.0.0"
        )
    )

    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
