# This is our attempt to create a simple web app that serves as a simple photo gallery.
# We will use Flask, Amazon RDS for storing user password, and Amazon S3 for storing the photos.
# This will eventually be deployed to an EC2 instance.
# We will use the following libraries:

from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
import hashlib
import boto3
import mysql.connector
from botocore.exceptions import NoCredentialsError
import requests
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi

app = Flask(__name__, template_folder='./templates', static_folder='./static') # Create a Flask app
app.secret_key = 'COMS422KHAAA'  # Secret key for flash messages

load_dotenv()

#access_token = False

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)
BUCKET_NAME = os.getenv('BUCKET_NAME')
# try:
#     response = s3.list_objects_v2(Bucket=BUCKET_NAME)
#     files = sorted([object for object in response['Contents']], key=lambda obj: obj['LastModified'], reverse=True)
#     print(files)

# except NoCredentialsError:
#     print("No AWS credentials found")


# Connect to MongoDB
mongo_conn_str = os.getenv('MONGO_URI')
client = MongoClient(mongo_conn_str, server_api=ServerApi('1'))

# DATABASE
db = client['photo_app']
users_collection = db['users']
photos_collection = db['photos']

# db = mysql.connector.connect(
#     host=os.getenv('DB_HOST'),
#     user=os.getenv('DB_USER'),
#     password=os.getenv('DB_PASSWORD'),
#     database=os.getenv('DB_NAME')
# )

# DEBUG MESSAGES
# if db.is_connected():
#     print("Connected to the database")
# else:
#     print("Failed to connect to the database")

# This is the home page of our web app.
@app.route('/')
def home():
    return render_template('./home.html')

def generate_sha256(text):
    hash_object = hashlib.sha256()
    encoded_text = text.encode('utf-8')
    hash_object.update(encoded_text)
    return hash_object.hexdigest()


@app.route('/submit', methods=['POST'])
def submit():
    user_id = request.form.get('user_id')
    user_password = request.form.get('user_pwd')
    hashed_password = generate_sha256(user_password)
    access_token = check_credentials(user_id, hashed_password)
    if access_token:
        # You can set the user_id in the session if needed
        session['user_id'] = user_id
        return redirect(url_for('gallery'))
    else:
        flash('Invalid user ID or password. Please try again.')
        return redirect(url_for('home')) 
    
def check_credentials(user_id, user_password): # In MongoDB
    response = users_collection.find_one({'user_id': user_id})
    if response and response['password'] == user_password:
        return True
    else:
        return False

# MongoDB method to get the photos of a user
@app.route('/gallery')
def gallery():
    if 'user_id' not in session:
        # Redirect to home page if user is not logged in
        flash('Please log in to view the gallery.')
        return redirect(url_for('home'))

    # Get the user ID from the session
    user_id = session['user_id']

    # Fetch the photos from the photos table where the user ID matches order by photo_id desc
    photos = photos_collection.find({'user_id': user_id}).sort('photo_id', -1)
    # Extract photo URLs from the fetched rows
    images = [photo['photo_url'] for photo in photos]

    # Render the gallery page with the list of images
    return render_template('gallery.html', images=images)

@app.route('/download/<path:image_name>')
def download_image(image_name):
    # Construct the S3 URL for the image
    image_url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{image_name}"

    # Fetch the image from S3
    response = requests.get(image_url, stream=True)

    # Check if the request was successful
    if response.status_code == 200:
        # Create a generator to stream the content
        def generate():
            for chunk in response.iter_content(chunk_size=4096):
                yield chunk

        # Send the streamed content as a file download
        return Response(generate(), headers={
            "Content-Disposition": f"attachment; filename={image_name}",
            "Content-Type": response.headers['Content-Type']
        })
    else:
        return "Failed to fetch image", 404
    
@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        flash('No file part')
        return redirect(url_for('home'))
    file = request.files['image']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('home'))
    if file:
        filename = file.filename 
        try:
            # Logic to upload to S3
            s3.upload_fileobj(
                file,
                BUCKET_NAME,
                filename
            )
            # Get the user ID from the session
            user_id = session.get('user_id')

            # Store the new photo URL in the MongoDB photos collection (photo_id, user_id, photo_url) (photo_id is auto inremented in MYSQL, we want the same in dynamoDB)
            photo_id = photos_collection.count_documents({}) + 1
            photo_url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{filename}"
            photos_collection.insert_one({'photo_id': photo_id, 'photo_url': photo_url, 'user_id': user_id})

            flash('File successfully uploaded')
        except Exception as e:
            flash(f'Failed to upload file: {e}')
        
        return redirect(url_for('gallery'))
    
@app.route('/logout', methods=['POST'])
def logout():
    # Clear the session
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('home'))

# Sign up using MongoDB
@app.route('/signup', methods=['POST'])
def signup():
    # Get the new user ID and password from the form
    new_user_id = request.form.get('new_user_id')
    new_user_password = request.form.get('new_user_pwd')
    hashed_password = generate_sha256(new_user_password)
    
    # Check if user already exists -- we will use MongoDB for this
    response = users_collection.find_one({'user_id': new_user_id})
    if response:
        flash('User ID already exists. Please choose a different one.')
        return redirect(url_for('home'))

    # Insert new user into the users table -- we will use MongoDB for this
    users_collection.insert_one({'user_id': new_user_id, 'password': hashed_password})

    flash('User successfully created. Please log in.')
    return redirect(url_for('home'))


# 404 Handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('./404.html'), 404


if __name__ == "__main__":
    app.run()
