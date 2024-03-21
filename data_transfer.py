import boto3
import json
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()


# Connect to MySQL RDS instance
mysql_db = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME')
)

# Connect to DynamoDB
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('dynamo_photo_users')
photos_table = dynamodb.Table('dynamo_photo_photos')

# Query data from MySQL USERS table
mysql_cursor = mysql_db.cursor()
mysql_cursor.execute('SELECT user_id, password FROM users')
users_rows = mysql_cursor.fetchall()

# Query data from MySQL photos table
mysql_cursor.execute('SELECT photo_id, user_id, photo_url FROM photos')
photos_rows = mysql_cursor.fetchall()

# Insert data into DynamoDB Users table
for row in users_rows:
    item = {
        'user_id': row[0],
        'password': row[1]
    }
    users_table.put_item(Item=item)

# Insert data into DynamoDB Photos table
for row in photos_rows:
    item = {
        'photo_id': row[0],
        'user_id': row[1],
        'photo_url': row[2]
    }
    photos_table.put_item(Item=item)

# Close MySQL connection
mysql_db.close()
