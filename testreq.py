import requests

url = 'http://127.0.0.1:5000/scrape'
data = {
    'business_name': '49 Seats - Orchard',
    'review_limit': 10,
    'sorted': 0
}

response = requests.post(url, json=data)
print(response.json())
