import boto3
import pandas as pd
import json

# Initialize the S3 client
s3 = boto3.client('s3')

# Define the bucket name and the file name
bucket_name = 'google-reviews-streamlit-db'
json_file_name = 'reviews_by_restaurant.json'

# Function to read JSON file from S3 and return list of restaurants
def get_restaurants_from_s3(bucket_name, json_file_name):
    response = s3.get_object(Bucket=bucket_name, Key=json_file_name)
    json_data = response['Body'].read().decode('utf-8')
    data = json.loads(json_data)
    restaurants = list(data.keys())
    return restaurants, data

# Function to convert reviews of a selected restaurant to DataFrame
def convert_to_dataframe(data, restaurant_name):
    reviews = data[restaurant_name]
    df = pd.DataFrame(reviews)
    return df

# Fetch the list of restaurants
restaurants, data = get_restaurants_from_s3(bucket_name, json_file_name)

# Print the list of restaurants
print("List of Restaurants:")
for i, restaurant in enumerate(restaurants, 1):
    print(f"{i}. {restaurant}")

# Example: Select a restaurant by its name
selected_restaurant = input("Enter the name of the restaurant to view its reviews: ")

# Convert the selected restaurant's reviews to DataFrame
if selected_restaurant in data:
    df = convert_to_dataframe(data, selected_restaurant)
    print(f"\nReviews for {selected_restaurant}:")
    print(df)
else:
    print(f"Restaurant '{selected_restaurant}' not found.")