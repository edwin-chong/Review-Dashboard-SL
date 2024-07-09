# Frontend for my Google Reviews Dashboard App

This app extracts Google Reviews and displays the data in meaningful charts. It also generates AI summaries of the reviews using pre-trained Natural Language Processing (NLP) models to provide users with a better understanding of the restaurant.

# Explanation of the stack used:

Main Programming Language: Python

Frontend: Created using Streamlit, a Python library for dashboard visualization, and deployed using Streamlit Share.

Backend: Created using Flask, deployed on an AWS EC2 instance. The Flask app handles HTTP requests from the frontend, performs backend logic, and returns the necessary information. It also updates files in an AWS S3 Bucket.

Scripts: The Flask app calls two Python scripts for scraping Google Reviews and generating AI summaries.

Data Storage: AWS S3 Bucket for fast and efficient data retrieval.

## Explanation of the App

### Sidebar Options

Users can choose a restaurant from a dropdown list or search for their desired restaurant.

#### If the restaurant is not found in the list

If the restaurant is not available in the dropdown list, a form will appear on the right side, allowing the user to input relevant details such as the restaurant's name, the number of reviews to scrape, and the order of the reviews (newest, oldest, or most relevant).

Note: The scraping API may not retrieve all reviews if a restaurant has more than 1000 reviews.

After filling in the details and clicking on 'Generate new data,' a HTTP POST request is sent to the backend Flask app, along with a HTTP GET request that polls the status at fixed intervals. The backend Flask app calls the script to scrape reviews, updates the AWS S3 Bucket with the new data, and returns an HTTP 200 success message to the frontend to notify the user.

If the restaurant cannot be found by the scraping script, an HTTP 500 error message is sent to the backend Flask app, notifying the Streamlit app of the failed request.

#### If the restaurant is in the list

If the restaurant is in the list, its reviews will be displayed on the right, along with some basic charts. Users can filter out reviews with no description and generate an AI summary of the reviews.

Users can view individual reviews in a dataframe, with columns for 'Review Date' (month and year) and 'Star Rating' (number of stars). A toggle button allows for adjustable table viewing.

Clicking 'Get AI summary of Review' sends an HTTP POST request to another backend API endpoint. The backend Flask app calls the relevant script, which feeds the reviews data into a pre-trained NLP model to generate the summary. The data is then returned to the frontend for display.

// If the restaurant can be found in the list, the reviews from the restaurant would be displayed on the right. Some basic analysis of the reviews would have been performed.
There is also an option to filter out reviews with no description, as well as a button to get an AI summary of the reviews.

After the charts, users can also view the individual reviews scraped from Google Reviews, in the form of a dataframe.  
The 'Review Date' column indicates the month and year of the review, and the 'Star Rating' column shows the number of stars given by the review.  
There is also a toggle button to make the table adjustable, for better viewing.

If the 'Get AI summary of Review' button is clicked, a HTTP post request would be sent to another backend API endpoint where the backend Flask App would call the relevant script, which will feed the reviews data into a pre-trained NLP model to get the executive summary of the reviews. After the generation is complete, the data is returned to the backend Flask App, which will forward the data back to the frontend for display.

## Explanation of Scraping script

Scraping is done using Python and libraries such as Selenium and BeautifulSoup. Upon execution, script will attempt to find the restaurant in Google Maps. If not found, the script will return a HTTP 500 error message.  
If found, the script will scrape the reviews, and perform some data cleaning, before saving the data to AWS S3 Bucket in JSON format.

## Explanation of NLP script

The AI summary is generated using Natural Language Processing models such as ChatGPT API. Due to the large size of string to be fed into the API, the reviews had to be separated and fed into the model in sequence. The returned data is then converted to JSON to be passed back to the backend Flask App, which then returns to the frontend, where it will peform some styling and formatting before display.

# Challenges

There were numerous challenges that I faced during the development of the project. The first problem was the scraping of Google Reviews. There were multiple efficiency issues during the scraping of Google Reviews.

## Challenges faced in Scraping

The most memorable one was getting the full description of each rating during the scraping process while ensuring the script does not run for too long. As Google hides reviews that were past a certain character limit, the scraper had to search and click the 'see more' button during the scraping process while scrolling to find more reviews, which can be time consuming. Eventually I found that the fastest way is to make Seleneium scroll the browser to the bottom as much as possible in order to show as many reviews as possible, then search and click the 'see more' button all at once.

Another challenge I faced here was the gradual slowdown in the selenium browser as more reviews are loaded. Initially, in order to make the script faster, I reduced the intervals between each action. However, as more reviews are being loaded, the browsers will start to slow down, causing my script to end before it was intended, as it assumed all the reviews has been found. This caused the script to return lesser review data as expected. This was eventually fixed by adding more layers of checks to ensure all reviews has been found, before progressing to the next stage.

## Challenges faced in NLP

Another significant challenge I faced was during the development of the NLP model. Initially, I had intended to train my own NLP model. The initial plan was to use the scikit-learn library to train a NLP model for sentiment analysis. After retrieving review data for dozens of restaurants, I used these data to train my NLP model. Preprocessing of the text such as noise removals were done using regular expressions using the re library and tokenization were done using the nltk library.

Code pic - Example of Noise removal using re

# Noise Removals

## Remove URLs

def remove_URL(text):
"""
Remove URLs from a sample string
"""
return re.sub(r"https?://\S+|www\.\S+", "", text)

## Remove non_ascii

def remove_non_ascii(text):
"""
Remove non-ASCII characters
"""
return re.sub(r'[^\x00-\x7f]',r'', text)

## Remove special characters

def remove_special_characters(text):
"""
Remove special special characters, including symbols, emojis, and other graphic characters
"""
emoji_pattern = re.compile(
'['
u'\U0001F600-\U0001F64F' # emoticons
u'\U0001F300-\U0001F5FF' # symbols & pictographs
u'\U0001F680-\U0001F6FF' # transport & map symbols
u'\U0001F1E0-\U0001F1FF' # flags (iOS)
u'\U00002702-\U000027B0'
u'\U000024C2-\U0001F251'
']+',
flags=re.UNICODE)
return emoji_pattern.sub(r'', text)

## Remove punctuations

def remove_punct(text):
"""
Remove the punctuation
"""
return text.translate(str.maketrans('', '', string.punctuation))

# Text Cleaning

## Lowercase

df['clean_review'] = df['review_description'].apply(lambda x: x.lower())

# ## Expand contractions

df['clean_review'] = df['clean_review'].apply(lambda x: contractions.fix(x))

# Noise Removals

## Remove URL

df['clean_review'] = df['clean_review'].apply(lambda x: remove_URL(x))

## Remove Non ASCII

df['clean_review'] = df['clean_review'].apply(lambda x: remove_non_ascii(x))

## Remove special chars

df['clean_review'] = df['clean_review'].apply(lambda x: remove_special_characters(x))

## Remove punctuation

df['clean_review'] = df['clean_review'].apply(lambda x: remove_punct(x))

Tokenization, removal of stop words, using NLTK
Stemming, POS tagging, Lemmatization
TF-IDF Vectorization, LDA Model, NMF model to find relevant topics from reivew data
Count Vectorization to get most common words/phrases

However, despite these, final result were not as desirable
pic of table

<!-- (Dont put yet. Did not code it out well) Using bert transformer to perform sentiment analysis - not as accurate (when compared to reviews left by users). no need to perform sentiment analysis as ratings were already given.  -->
