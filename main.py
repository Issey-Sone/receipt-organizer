import os
import pprint
import requests
from flask import Flask, request, render_template, jsonify, redirect, url_for, session, flash
import json
from pymongo import MongoClient, errors
from io import BytesIO
import pandas as pd
from google.cloud import storage
import openai
from bson.json_util import dumps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'asdfskfjkassdakf140-1'

#chatgpt
openai.api_key = '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'

# Directory to store uploaded receipts
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#Taggun OCR
TAGGUN_API_URL = "https://api.taggun.io/api/receipt/v1/verbose/file"
TAGGUN_API_KEY = "7aa60b606a0f11eea8f313266e4aecd5"

#mongoDB
MONGODB_URI = 'mongodb+srv://Bomb3077:Pxmf3cmQ80EdLwoa@cluster0.arkmrqj.mongodb.net/?retryWrites=true&w=majority'
db_name = 'receiptOrganizer'

#Google Cloud
json_key_path = "strategic-grove.json"
bucket_name = "receipts001"

def generating_category(desired_json):
    messages = [ {"role": "system", "content":  
              "You are a receipt organizer that return the category in one single word based on the merchant name and products given."} ]
    message = "Merchant name is " + desired_json.get("merchantName") + "and items are "
    for item in desired_json.get("productLineItems", []):
        message += item.get('name', '')
        message += ", "
    messages.append({"role": "user", "content": message})
    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    category = chat.choices[0].message.content
    return category


def upload_image_to_gcs(image_name, file_path, category):

    # Create a client using the service account JSON file
    storage_client = storage.Client.from_service_account_json(json_key_path)

    # Get the bucket
    bucket = storage_client.bucket(bucket_name)

    # Define the destination blob
    destination_blob_name = f"{category}/{image_name}.jpg"
    blob = bucket.blob(destination_blob_name)
    blob.content_type = "image/jpeg"

    # Upload the file
    with open(file_path, "rb") as f:
        blob.upload_from_file(f)

    print("Image Uploaded:", destination_blob_name)


def process_receipt_with_taggun(filename, file_path):

    headers = {
        "apikey": TAGGUN_API_KEY,
        "accept": "application/json",
    }
    files = {"file": (filename, open(file_path, 'rb'), "image/jpeg")}
    payload = {
        "refresh": "false",
        "incognito": "false",
        "extractTime": "false",
        "extractLineItems": "true"
    }
    response = requests.post(TAGGUN_API_URL, data=payload, headers=headers, files=files)

    return response.json()


def convert_to_desired_json(taggun_response, username):
    desired_json = {
        "username": username,
        "date": taggun_response.get('date', {}).get('data', ''),
        "productLineItems": [],
        "merchantAddress": taggun_response.get('merchantAddress', {}).get('data', ''),
        "merchantName": taggun_response.get('merchantName', {}).get('data', ''),
        "totalAmount": taggun_response.get('totalAmount', {}).get('data', ''),
        "currencyCode": taggun_response.get('totalAmount', {}).get('currencyCode', ''),
    }

    # Convert product line items to desired format
    product_line_items = taggun_response.get('entities', {}).get('productLineItems', [])
    for item in product_line_items:
        desired_json["productLineItems"].append({
            "name": item.get('data', {}).get('name', {}).get('data', ''),
            "quantity": item.get('data', {}).get('quantity', {}).get('data', ''),
            "totalPrice": item.get('data', {}).get('totalPrice', {}).get('data', ''),
            "unitPrice": item.get('data', {}).get('unitPrice', {}).get('data', ''),
        })

    return desired_json

def store_desired_json(collection_name, desired_json):
    client = MongoClient(MONGODB_URI)
    db = client[db_name]
    collection = db[collection_name]
    collection.insert_one(desired_json)
    client.close()

def check_password(username, password):
    client = MongoClient(MONGODB_URI)
    db = client[db_name]
    user_collection = db['users']
    query = {'username': username, 'password': password}
    res = user_collection.find_one(query)
    client.close()
    return bool(res)

def check_existense(username):
    client = MongoClient(MONGODB_URI)
    db = client[db_name]
    user_collection = db['users']
    query = {'username': username}
    res = user_collection.find_one(query)
    client.close()
    return bool(res)

def insert_user(username, password):
    client = MongoClient(MONGODB_URI)
    db = client[db_name]
    user_collection = db['users']
    query = {'username': username, 'password': password}
    user_collection.insert_one(query)
    client.close()


def pull_categories():
    client = MongoClient(MONGODB_URI)
    db = client[db_name]
    categories = db.list_collection_names()
    client.close()
    for i in range(len(categories)):
        if categories[i] == 'users':
            categories.pop(i)
            return categories
    return categories

def pull_receipts(catagory):
    receipts = []
    try:
        client = MongoClient(MONGODB_URI)
        db = client[db_name]
        collection = db[catagory]
        cursor = collection.find({})
        for receipt in cursor:
            receipts.append(receipt)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        client.close()
    return receipts


def get_receipt_by_id(receipt_id, category):
    try:
        client = MongoClient(MONGODB_URI)
        db = client[db_name]
        collection = db[category]
        # Assuming 'receipts_collection' is your MongoDB collection
        receipt = collection.find_one({'_id': receipt_id})
        return receipt
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
    finally:
        client.close()

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    categories = pull_categories()
    return render_template('index.html', categories=categories)


@app.route('/category/<category>')
def extend_index(category):
    if 'user' not in session:
        return redirect(url_for('login'))
    categories = pull_categories()
    receipts = pull_receipts(category)
    return render_template('index.html', categories=categories, receipts=receipts)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Retrieve form data and store in the database
        username = request.form['username']
        password = request.form['password']
        # Store the user information in MongoDB (you may want to hash the password)
        if check_existense(username):
            flash(f'{username} already exist') 
        else:
            insert_user(username, password)
            flash(f'{username} created successfully!')
        return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if check_existense(username)==True:
            if check_password(username, password)==True:
                session['user'] = username
                return redirect(url_for('index'))
            else:
                flash('wrong password')
        else:
            flash(f"{username} not exist")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Implement your logout logic
    session.clear()
    return redirect(url_for('login'))


@app.route('/upload', methods=['POST'])
def upload_receipt():
    file = request.files['file']

    if file:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        # Process the receipt using TAGGUN API
        taggun_response = process_receipt_with_taggun(filename, file_path)
        # Convert the structure to desired Json
        desired_json = convert_to_desired_json(taggun_response, session['user'])
        category = generating_category(desired_json)
        # Testing
        # json_data = json.dumps(desired_json)
        store_desired_json(category, desired_json)
        upload_image_to_gcs(filename, file_path, category)
        flash('successful upload receipt')
    flash('no such file exist')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)