from flask import Flask, request, jsonify, render_template, redirect, url_for

import bcrypt
import requests
import pyrebase
import firebase_admin
from firebase_admin import credentials, storage, firestore
import uuid
from dotenv import load_dotenv
import os
load_dotenv()
api_key = os.getenv('API_KEY')

cred = credentials.Certificate("/Users/samyukthasudheer/retrove/retrove-app-firebase-adminsdk-onzln-141c93b6a8.json")
firebase_admin.initialize_app(cred)
bucket = storage.bucket('retrove-app.appspot.com')
db = firestore.Client() 
session = {"is_logged_in": False, "name": "", "email": "", "uid": ""}
app = Flask(__name__, static_url_path='/static', static_folder='static')

firebaseConfig = {
  'apiKey': api_key,
  'databaseURL': 'https://retrove-app-default-rtdb.asia-southeast1.firebasedatabase.app',
  'authDomain': "retrove-app.firebaseapp.com",
  'projectId': "retrove-app",
  'storageBucket': "retrove-app.appspot.com"
  
}


firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
database = firebase.database()




@app.route("/")
def login():
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        result = request.form
        email = result["email"]
        password = result["password"]
        name = result["name"]
        try:
            auth.create_user_with_email_and_password(email, password)
            user = auth.sign_in_with_email_and_password(email, password)
            data = {"name": name, "email": email}
            database.child("users").child(user["localId"]).set(data)
            return redirect(url_for('index'))
        except Exception as e:
            print(e)  # Print the error for debugging
            return redirect(url_for('login'))  # Redirect to registration page on error

    return render_template('register.html')  # Redirect to registration page if method is not POST
@app.route("/signin", methods = ["POST", "GET"])
def signin():
    if request.method == "POST":        #Only if data has been posted
        result = request.form           #Get the data
        email = result["email"]
        password = result["pass"]
        try:
            #Try signing in the user with the given information
            user = auth.sign_in_with_email_and_password(email, password)
            #Insert the user data in the global person
            global person
            session["is_logged_in"] = True
            session["email"] = user["email"]
            session["uid"] = user["localId"]
            #Get the name of the user
            data = database.child("users").get()
            session["name"] = data.val()[session["uid"]]["name"]
            #Redirect to welcome page
            return redirect(url_for('index'))
        except:
            #If there is any error, redirect back to login
            return redirect(url_for('login'))
    else:
        if session["is_logged_in"] == True:
            return redirect(url_for('index'))
        
    return render_template("login.html")

@app.route('/index')
def index():
    return render_template("index.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/upload_product', methods=['GET', 'POST'])
def upload_product():
    if request.method == 'POST':
        title = request.form['title']
        image_file = request.files['image']
        description = request.form['description']
        product_type = request.form['type']
        price = request.form['price']
        # Validate file type and size
        if not image_file.mimetype.startswith('image/'):
            return 'Invalid image file format. Please upload an image file.'
        if image_file.content_length > 10 * 1024 * 1024:  # 10MB limit
            return 'Image file too large. Please upload a file under 10MB.'

        # Generate a unique filename and upload to Firebase Storage
        blob = bucket.blob(f'{uuid.uuid4()}.{image_file.mimetype.split("/")[-1]}')
        blob.upload_from_string(image_file.read(), content_type=image_file.mimetype)

        # Update product data in Firebase Storage and Firestore (or Realtime Database)
        data = {
            "title": title,
            "image_url": blob.public_url,
            "description": description,
            "type": product_type,
            "price": price
        }

         # Replace with your database instance
        if product_type == "sell":
            db.collection("sell").add(data)
        elif product_type == "rent":
            db.collection("rent").add(data)
        else:
            return "Invalid product type."

        return redirect(url_for('index'))

    return render_template('upload.html')

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if request.method == 'POST':
        # Extract data from the form
        title = request.form['title']
        image_file = request.files['image']
        fromperson = request.form['from']
        donatedto = request.form['to']
        description = request.form['description']
        
        # Handle image upload
        if not image_file.mimetype.startswith('image/'):
            return 'Invalid image file format. Please upload an image file.'
        if image_file.content_length > 10 * 1024 * 1024:  # 10MB limit
            return 'Image file too large. Please upload a file under 10MB.'

        # Generate a unique filename and upload to Firebase Storage
        blob = bucket.blob(f'{uuid.uuid4()}.{image_file.mimetype.split("/")[-1]}')
        blob.upload_from_string(image_file.read(), content_type=image_file.mimetype)


        # Create a new document in the donate collection
       
        data = {
            'title': title,
            'fromperson': fromperson,
            'donatedto': donatedto,
            "image_url": blob.public_url,
            "description": description
            # Replace with actual image URL after upload
            # Add other fields as needed
        }
        db.collection('donate').add(data)

        return redirect(url_for('index'))

    return render_template('donate.html')

@app.route('/buys')
def buys():
    # Get all documents from the sell collection
    products = db.collection('sell').get()

    # Convert the query snapshot to a list of dictionaries
    products_list = [doc.to_dict() for doc in products]
    print(products_list)
    return render_template('buys.html', products=products_list)

@app.route('/rentals')
def rentals():
    # Get all documents from the sell collection
    products = db.collection('rent').get()

    # Convert the query snapshot to a list of dictionaries
    products_list = [doc.to_dict() for doc in products]
    print(products_list)
    return render_template('buys.html', products=products_list)

@app.route('/media')
def media():
    return render_template("media.html")

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user_id = session.get('uid')
    if not session["is_logged_in"]:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    data = {
        "user_id": user_id,
        "product_id": product_id
    }
    
    db.collection('cart').add(data)

    # Consider updating UI or redirecting to cart page
    return 'Product added to cart!'
@app.route('/cart')
def cart():
    docs = (
    db.collection("cart")
    .where(filter=FieldFilter("user_id", "==", session['uid']))
    .stream())
    render_template('cart.html', docs)
@app.route('/logout')
def logout():
    session = {"is_logged_in": False, "name": "", "email": "", "uid": ""}
    return redirect(url_for('login'))

@app.route('/map')
def map():
    return render_template("map.html")

@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")
if __name__ == '__main__':
    app.run(debug=True)