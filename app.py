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

#Connect to DynamoDB
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('dynamo_photo_users')
photos_table = dynamodb.Table('dynamo_photo_photos')

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

# def check_credentials(user_id, user_password):
#     # Use a context manager to ensure the database connection is closed properly
#     with db.cursor() as cursor:
#         cursor.execute("USE photo_gallery")

#         query = "SELECT password FROM users WHERE user_id = %s"
#         values = (user_id,)

#         cursor.execute(query, values)

#         result = cursor.fetchone()
    
#     # Check if the user ID and password combination exists
#     if result and result[0] == user_password:
#         return True  # User ID and hashed password combination exists
#     else:
#         return False  # User ID and hashed password combination does not exist
    
def check_credentials(user_id, user_password):
    response = users_table.get_item(Key={'user_id': user_id})
    if 'Item' in response:
        if response['Item']['password'] == user_password:
            return True
    return False

@app.route('/gallery')
def gallery():
    if 'user_id' not in session:
        # Redirect to home page if user is not logged in
        flash('Please log in to view the gallery.')
        return redirect(url_for('home'))

    # Get the user ID from the session
    user_id = session['user_id']

    # Fetch the photos from the photos table where the user ID matches
    response = photos_table.scan(FilterExpression=boto3.dynamodb.conditions.Attr('user_id').eq(user_id))
    photos = response['Items']
    photos.sort(key=lambda photo: photo['photo_id'], reverse=True)

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

            # Store the new photo URL in the DYNAMO DB photos table (photo_id, user_id, photo_url) (photo_id is auto inremented in MYSQL, we want the same in dynamoDB)
            photo_id = len(photos_table.scan()['Items']) + 1 # Get the next photo ID
            photo_url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{filename}"
            photos_table.put_item(Item={
                'photo_id': photo_id,
                'user_id': user_id,
                'photo_url': photo_url
            })

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

@app.route('/signup', methods=['POST'])
def signup():
    # Get the new user ID and password from the form
    new_user_id = request.form.get('new_user_id')
    new_user_password = request.form.get('new_user_pwd')
    hashed_password = generate_sha256(new_user_password)
    
    # Check if user already exists -- we will use DynamoDB for this
    response = users_table.get_item(Key={'user_id': new_user_id})
    if 'Item' in response:
        flash('User ID already exists. Please log in.')
        return redirect(url_for('home'))

    # Insert new user into the users table -- we will use DynamoDB for this
    users_table.put_item(Item={
        'user_id': new_user_id,
        'password': hashed_password
    })

    flash('User successfully created. Please log in.')
    return redirect(url_for('home'))


# 404 Handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('./404.html'), 404


if __name__ == "__main__":
    app.run()
