from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import csv


from dotenv import load_dotenv
import os

load_dotenv()


uri = os.getenv('MONGO_URI')

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# DATABASE
db = client['photo_app']
users_collection = db['users']
photos_collection = db['photos']

# Delete all documents from the users collection
users_collection.delete_many({})

# Delete all documents from the photos collection
photos_collection.delete_many({})

#Load User and passwords into the database from migration_data folder -> users.csv

with open('migration_data/users.csv', 'r') as file:
    reader = csv.reader(file)
    next(reader)
    for row in reader:
        user = {
            'user_id': row[0],
            'password': row[1]
        }
        users_collection.insert_one(user)

#Load photos into the database from migration_data folder -> photos.csv
with open('migration_data/photos.csv', 'r') as file:
    reader = csv.reader(file)
    next(reader)
    for row in reader:
        photo = { #photo_id is an integer
            'photo_id': int(row[0]),
            'photo_url': row[1],
            'user_id': row[2],
        }
        photos_collection.insert_one(photo)
#Check if the data was loaded into the database
print(users_collection.find_one())
print(photos_collection.find_one())

