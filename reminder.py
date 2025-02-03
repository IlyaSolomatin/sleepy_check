import os
from google.cloud import firestore
from telegram.ext import Application

TOKEN = os.getenv("TOKEN")
project_id = 'dynamic-now-724'
database = 'sleepy' 
data_collection = 'records'
db = firestore.Client(project=project_id, database=database)

async def send_reminders():
    # Get all documents and extract unique user_ids
    docs = db.collection(data_collection).select(['user_id']).stream()
    user_ids = list(set(doc.get('user_id') for doc in docs))

    application = Application.builder().token(TOKEN).build()
    
    for user_id in user_ids:
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text="What's your sleep score now? Send a number from 1 to 10"
            )
        except Exception as e:
            print(f"Failed to send message to user {user_id}: {str(e)}")

    await application.shutdown()

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_reminders())
