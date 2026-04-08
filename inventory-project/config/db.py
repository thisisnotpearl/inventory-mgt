from mongoengine import connect
import dotenv
import os
dotenv.load_dotenv()  # loads your .env file into os.environ automatically

url = os.environ['MONGODB_URI']
db = os.environ['MONGODB_DB_NAME']

def init_db():
    connect(db, host=url)
    print("Connected to MongoDB successfully!")
    