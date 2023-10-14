import os
import requests
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

# Directory to store uploaded receipts
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

TAGGUN_API_URL = "https://api.taggun.io/api/receipt/v1/verbose/file"
TAGGUN_API_KEY = "7aa60b606a0f11eea8f313266e4aecd5"

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



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_receipt():
    file = request.files['file']

    if file:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        # Process the receipt using TAGGUN API
        taggun_response = process_receipt_with_taggun(filename, file_path)

        # You can now handle the taggun_response as needed (e.g., save to database)
        # For simplicity, we'll just return the JSON response from TAGGUN API
        return jsonify(taggun_response)

    return "No file selected."

if __name__ == '__main__':
    app.run(debug=True)
