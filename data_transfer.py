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

#Load User and passwords into the database from migration_data folder -> users.csv

with open('migration_data/users.csv', 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        user = {
            'user_id': row[0],
            'password': row[1]
        }
        users_collection.insert_one(user)

#Load photos into the database from migration_data folder -> photos.csv
with open('migration_data/photos.csv', 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        photo = {
            'photo_id': row[0],
            'photo_url': row[1],
            'user_id': row[2],
        }
        photos_collection.insert_one(photo)
#Check if the data was loaded into the database
print(users_collection.find_one())
print(photos_collection.find_one())

# Get the first document in the users collection
first_user = users_collection.find_one()

# Delete the first document in the users collection
users_collection.delete_one({'_id': first_user['_id']})

# Get the first document in the photos collection
first_photo = photos_collection.find_one()

# Delete the first document in the photos collection
photos_collection.delete_one({'_id': first_photo['_id']})

#Check if the data was deleted from the database
print(users_collection.find_one())
print(photos_collection.find_one())


