import requests

url = "https://api.taggun.io/api/receipt/v1/verbose/file"

files = { "file": ("OR%20sample001.jpg", open("OR%20sample001.jpg", "rb"), "image/jpeg") }
payload = {
    "refresh": "false",
    "incognito": "false",
    "extractTime": "true",
    "language": "en",
    "extractLineItems": "true"
}
headers = {
    "accept": "application/json",
    "apikey": "7aa60b606a0f11eea8f313266e4aecd5"
}

response = requests.post(url, data=payload, files=files, headers=headers)

print(response.text)