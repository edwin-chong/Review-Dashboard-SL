import requests
from dotenv import load_dotenv
import os
load_dotenv()

base_url = os.getenv('FLASK_APP_URL')
# base_url = 'http://127.0.0.1:5000'
if os.getenv('PRODUCTION') == 'True':
    base_url= os.getenv('FLASK_APP_PROD_URL')

url = f'{base_url}/scrape'
print(url)
# data = {
#     'business_name': '49 Seats - Orchard',
#     'review_limit': 10,
#     'sorted': 0
# }

# response = requests.post(url, json=data)
# print(response.json())
