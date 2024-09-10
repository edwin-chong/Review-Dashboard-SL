import boto3
import json
import pandas as pd
import streamlit as st
import requests
import altair as alt
from st_keyup import st_keyup
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import logging
import pytz
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import warnings

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*Could not infer format.*")

# Turn off logging for botocore
logging.getLogger('botocore').setLevel(logging.CRITICAL)

# Initialize the S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
    region_name=st.secrets["AWS_DEFAULT_REGION"]
)

# Define the bucket name and the file name
bucket_name = st.secrets["S3_BUCKET_NAME"]
json_file_name = st.secrets["S3_JSON_NAME"]
flask_url = st.secrets["FLASK_APP_URL"]

@st.cache_data(ttl=3600)
def load_and_process_data(bucket_name, json_file_name, bypass_cache=False):
    if bypass_cache:
        st.cache_data.clear()

    response = s3.get_object(Bucket=bucket_name, Key=json_file_name)
    json_data = response['Body'].read().decode('utf-8')
    data = json.loads(json_data)
    reviews_df = {}
    summary_dict = {}
    ngrams_dict = {}
    last_modified_dict = {}
    for restaurant, restaurant_info in data.items():
        reviews = restaurant_info['data']
        df = pd.DataFrame(reviews)
        df['DateOfReview'] = pd.to_datetime(df['DateOfReview'], format='%Y-%m-%d')
        df = df.sort_values(by='DateOfReview', ascending=False)
        df['StarRating'] = pd.to_numeric(df['StarRating'])
        df['month_year'] = df['DateOfReview'].dt.to_period('M').dt.to_timestamp().dt.strftime('%b-%Y')
        df['DateOfReview'] = df['DateOfReview'].dt.date
        reviews_df[restaurant] = df.reset_index(drop=True)  

        summary_dict[restaurant] = restaurant_info['summary']
        ngrams_dict[restaurant] = restaurant_info['ngram']
        last_modified_dict[restaurant] = restaurant_info['last_modified']

        print('Restaurant info summary:')
        print(restaurant_info['last_modified'])

    logger.info('reviews_df reloaded')
    return list(reviews_df.keys()), reviews_df, summary_dict, ngrams_dict, last_modified_dict

def check_for_updates(bucket_name, json_file_name):
    response = s3.head_object(Bucket=bucket_name, Key=json_file_name)
    updated_time = response['LastModified']
    
    # Convert last_modified to Singapore time
    updated_time = updated_time.astimezone(pytz.timezone('Asia/Singapore'))

    logger.info(f'Live DB last modified date: {updated_time}')
    return updated_time

def poll_status():
    logger.info('Polling status')
    if st.session_state.request_id:
        status_url = f'{flask_url}/status/{st.session_state.request_id}'
        response = requests.get(status_url)
        status = response.json().get('status')
        st.session_state.status = status
        logger.info(f"Status: {status}")

def send_scraping_request(res_name, loc_name, review_limit):
    url = f'{flask_url}/scrape'
    reviews_df = {
        'business_name': f'{res_name} - {loc_name}',
        'sort_order': 'Newest',
        'review_limit': str(review_limit)
    }
    response = requests.post(url, json=reviews_df)
    return response.json().get('request_id')

def analyze_reviews(res_name, df):
    url = f'{flask_url}/analyze'
    reviews_df = {"res_name": res_name, "reviews": df.to_dict(orient='records')}
    response = requests.post(url, json=reviews_df)
    if response.status_code == 200:
        logger.info("Success:")
    else:
        logger.error(f"Request failed with status code: {response.status_code}")

def remove_review(res_name):
    url = f'{flask_url}/remove_review/{res_name}'
    response = requests.delete(url)
    if response.status_code == 200:
        logger.info(f"Review information for {res_name} has been removed")
    elif response.status_code == 404:
        logger.info(f'Review information for {res_name} not found')
    else:
        logger.error(f"Request failed with status code: {response.status_code}")


def display_charts(selected_df):

    col1, col2 = st.columns([3, 2])
    with col1:
        show_empty_reviews = st.checkbox('Include reviews with no description', True)
    with col2:
        filtered_df = selected_df if show_empty_reviews else selected_df[selected_df['ReviewDescription'] != 'nil']
        st.write(f"Displaying {len(filtered_df)} reviews") # Showing 100

    ratingGroupedDf = filtered_df.groupby('StarRating').size().reset_index(name='Count')
    average_rating = round(filtered_df['StarRating'].mean(), 2)
    chart = alt.Chart(ratingGroupedDf).mark_bar().encode(
        x=alt.X('StarRating:N', title='Star Rating', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Count:Q', title='Count'),
    ).properties(width=600, height=200)

    monthlyGroupedDf = filtered_df.groupby('month_year')['StarRating'].agg(['mean', 'count']).reset_index()
    monthlyGroupedDf.columns = ['Date', 'Star Rating', 'Num_Reviews']
    monthlyGroupedDf['Star Rating'] = round(monthlyGroupedDf['Star Rating'], 2)
    line_chart = alt.Chart(monthlyGroupedDf).mark_line(point=True).encode(
        x=alt.X('Date:T', title='Date [Month]'),
        y=alt.Y('Star Rating:Q', title='Average Star Rating'),
        tooltip=['Date:T', 'Star Rating:Q', 'Num_Reviews:Q']
    ).properties(width=600, height=200)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Average Star Rating Over Time')
        st.altair_chart(line_chart, use_container_width=True)
    with col2:
        st.subheader(f'Average Star Rating: {average_rating:.2f} ★')
        st.altair_chart(chart, use_container_width=True)
    st.divider()
    return filtered_df

def display_reviews_df(filtered_df):
    filtered_df = filter_dataframe(filtered_df)
    st.write(f'Displaying {len(filtered_df)} reviews') # showing 98
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(":red[(Double click to see the full description of each rating)]")
    with col2:
        adjustable_table = st.checkbox('Adjustable table')
    if adjustable_table:
        values = st.slider(":red[Drag slider to adjust width of dataframe]", 200, 1000, 600)
    filtered_df = filtered_df.reset_index(drop=True)
    st.dataframe(filtered_df[['month_year', 'ReviewDescription', 'StarRating']], use_container_width=True, width=values if adjustable_table else None)

def initialize_session_state():
    if 'status' not in st.session_state:
        st.session_state.status = 'Ready'
    if 'last_modified_time' not in st.session_state:
        st.session_state.last_modified_time = datetime.min.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Singapore'))
    if 'restaurant_names' not in st.session_state:
        st.session_state.restaurant_names = []
    if 'reviews_df' not in st.session_state:
        st.session_state.reviews_df = {}
    if 'summary_dict' not in st.session_state:
        st.session_state.summary_dict = {}
    if 'ngrams_dict' not in st.session_state:
        st.session_state.ngrams_dict = {}
    if 'last_modified_dict' not in st.session_state:
        st.session_state.last_modified_dict = {}
    if 'request_id' not in st.session_state:
        st.session_state.request_id = None
    if 'refresh_interval' not in st.session_state:
        st.session_state.refresh_interval = 300000  # Default to 5 minutes

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
                logger.debug(col)
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    cols_to_filter = ['StarRating', 'month_year']

    # Initialize session state for filters
    if 'filters' not in st.session_state:
        st.session_state.filters = {col: None for col in cols_to_filter}

    col1, col2 = st.columns((5,1))
    with col1:
        st.subheader('Reviews')
    with col2:
        # Add reset button to clear filters
        reset_button = st.button(':red[Reset filters]')

    if reset_button:
        st.session_state.filters = {col: None for col in cols_to_filter}

    modification_container = st.expander("Filters", expanded=False)

    
    with modification_container:
    # Handle 'StarRating' column
        if 'StarRating' in cols_to_filter:
            _, right = st.columns((1, 20))
            
            # Set fixed min and max values for StarRating
            min_value = 1
            max_value = 5
            
            # Retrieve or set default slider values
            default_values = st.session_state.filters.get('StarRating', (min_value, max_value))
            
            # Ensure default_values is a tuple (min_value, max_value)
            if not isinstance(default_values, tuple):
                default_values = (min_value, max_value)

            user_num_input = right.slider(
                "Filter Star Rating",
                min_value=min_value,
                max_value=max_value,
                value=default_values,
                step=1,
            )
            # Ensure the output is a tuple
            if isinstance(user_num_input, int):
                user_num_input = (user_num_input, user_num_input)

            st.session_state.filters['StarRating'] = user_num_input
            
            # Apply the filter
            df = df[df['StarRating'].between(*user_num_input)]

            # Check if the filtered DataFrame is empty
            if df.empty:
                st.warning("No results found for the selected Star Rating.")
                st.stop()

        # Handle 'month_year' column
        if 'month_year' in cols_to_filter:
            left, right = st.columns((1, 20))
            
            # Convert datetime column to month-year format
            df['MonthYear'] = df['month_year'].dt.to_period('M').astype(str)
            
            # Get unique sorted month-year values
            unique_month_years = sorted(df['MonthYear'].unique())
            
            # Retrieve or set default start and end dates
            # default_values = st.session_state.filters.get('month_year', (unique_month_years[0], unique_month_years[-1]))

            # if not isinstance(default_values, tuple) or default_values is None:
            default_values = (unique_month_years[0], unique_month_years[-1])
            
            default_start, default_end = default_values
            
            if default_start not in unique_month_years:
                default_start = unique_month_years[0]
                
            if default_end not in unique_month_years:
                default_end = unique_month_years[-1]
            
            # Display selection boxes for date range
            col1, col2 = st.columns(2)
            with col1:
                start_date_str = st.selectbox("Start date", unique_month_years, index=unique_month_years.index(default_start))
            with col2:
                end_date_str = st.selectbox("End date", unique_month_years, index=unique_month_years.index(default_end))
            
            # Convert selected month-year strings back to datetime objects for filtering
            start_date = pd.to_datetime(start_date_str, format='%Y-%m')
            end_date = pd.to_datetime(end_date_str, format='%Y-%m') + pd.offsets.MonthEnd(1)
            
            # Validate and apply the date range filter
            if start_date > end_date:
                st.error("Start date must be before or equal to end date")
            else:
                st.session_state.filters['month_year'] = (start_date_str, end_date_str)
                df = df.loc[df['month_year'].between(start_date, end_date)]

                # Check if the filtered DataFrame is empty
                if df.empty:
                    st.warning("No results found for the selected date range.")
                    st.stop()

            # Convert 'month_year' to desired string format for display
            df['month_year'] = df['month_year'].dt.strftime('%b-%Y')

    return df
    
def main():
    initialize_session_state()

    updated_time = check_for_updates(bucket_name, json_file_name)
    if st.session_state.last_modified_time.tzinfo is None:
        st.session_state.last_modified_time = st.session_state.last_modified_time.replace(tzinfo=pytz.UTC)
    st.session_state.last_modified_time = st.session_state.last_modified_time.astimezone(pytz.timezone('Asia/Singapore'))
    logger.info(f'Cached DB last modified date: {st.session_state.last_modified_time}')

    if updated_time > st.session_state.last_modified_time:
        restaurant_names, reviews_df, summary_dict, ngrams_dict, last_modified_dict = load_and_process_data(bucket_name, json_file_name, bypass_cache=True)
        st.session_state.restaurant_names = restaurant_names
        st.session_state.reviews_df = reviews_df
        st.session_state.summary_dict = summary_dict
        st.session_state.ngrams_dict = ngrams_dict
        st.session_state.last_modified_time = updated_time
        st.session_state.last_modified_dict = last_modified_dict
        logger.info(f'Updated DB last modified time: {st.session_state.last_modified_time}')
    else:
        restaurant_names = st.session_state.restaurant_names
        reviews_df = st.session_state.reviews_df
        summary_dict = st.session_state.summary_dict
        ngrams_dict = st.session_state.ngrams_dict
        last_modified_dict = st.session_state.last_modified_dict
        
    st.sidebar.title('Search for your restaurant from the list below.')
    st.sidebar.subheader(':blue[If your desired restaurant is not found, there will be an option to extract the reviews.]')
    st.sidebar.divider()

    if st.session_state.status:
        if st.session_state.status == 'Completed':
            st.sidebar.subheader(f':large_green_circle: Scraping request for {st.session_state.res_name} has completed, please refresh page!')
            st.cache_data.clear()
            st.session_state.request_id = None
            st.session_state.status = 'Ready'
            st.session_state.refresh_interval = 300000  # Reset to 5 minutes
        elif 'Failed' in st.session_state.status:
            st.sidebar.subheader(f':large_orange_circle: Scraping request for {st.session_state.res_name} has failed. Please try again with a different name')
            st.session_state.request_id = None
            st.session_state.status = 'Ready'
            st.session_state.refresh_interval = 300000  # Reset to 5 minutes
        elif 'In Progress' in st.session_state.status:
            st.sidebar.subheader(f':large_yellow_circle: Scraping request for {st.session_state.res_name} sent! Please check back later!')

    with st.sidebar:
        search_term = st_keyup("Search for the name of your restaurant here", key="0")
        st.session_state.search_term = search_term

    if 'filtered_restaurant_names' not in st.session_state:
        st.session_state.filtered_restaurant_names = restaurant_names

    if st.session_state.search_term:
        st.session_state.filtered_restaurant_names = [name for name in restaurant_names if st.session_state.search_term.lower() in name.lower()]
    else:
        st.session_state.filtered_restaurant_names = restaurant_names

    st_autorefresh(interval=st.session_state.refresh_interval, key="poll_status")
    selected_restaurant = st.sidebar.selectbox('Or select one from the list below:', st.session_state.filtered_restaurant_names)

    logger.info(f'Status: {st.session_state.status}')
    poll_status()

    if selected_restaurant not in restaurant_names:
        st.subheader(':red[Restaurant not found!]')
        st.write('Please try a different name. If the restaurant cannot be found from the list, you can request for it. (Will take up to 5 minutes, depending on the amount of reviews)')

        res_name = st.text_input('Name of restaurant :red[*]')
        loc_name = st.text_input('Location/Branch?')
        review_limit = st.number_input('Maximum no. of reviews to fetch: :red[*]', min_value=1, value=100, step=1)

        generate_new_data = st.button('Scrape reviews')
        if generate_new_data:
            st.session_state.res_name = res_name
            st.session_state.request_id = send_scraping_request(res_name, loc_name, review_limit)
            st.session_state.refresh_interval = 10000  # Set to 10 seconds
            logger.info(f'Scrape initiated. Request ID: {st.session_state.request_id}')
            poll_status()
            st.rerun()
            # st.session_state.status = 'In Progress'

        selected_df = pd.DataFrame(columns=['DateOfReview', 'StarRating', 'month_year', 'ReviewDescription'])
    else:
        st.subheader("Selected Restaurant:")
        col1, col2 = st.columns((1,1))
        with col1:
            st.title(f':green[{selected_restaurant}]')
            last_modified_scrape = last_modified_dict[selected_restaurant]['scrape']
            last_modified_scrape = 'NA' if last_modified_scrape == '' else last_modified_scrape
            st.write(f'Last fetched date: {last_modified_scrape}')
        # with col2:
        #     remove_review_button = st.button(':red[DELETE INFORMATION FOR THIS RESTAURANT]')
        #     if remove_review_button:
        #         remove_review(selected_restaurant)
        #         restaurant_names, reviews_df, summary_dict, ngrams_dict, last_modified_dict = load_and_process_data(bucket_name, json_file_name, bypass_cache=True)
        #         st.session_state.filtered_restaurant_names = restaurant_names
        #         st.rerun()
        
        st.divider()
        
        st.subheader(f'What users are saying about :green[{selected_restaurant}]')
        # last_modified_ngram = last_modified_dict[selected_restaurant]['ngram']
        # last_modified_ngram = 'NA' if last_modified_ngram == '' else last_modified_ngram
        # st.write(f'Last fetched date: {last_modified_ngram}')

        # col1, col2 = st.columns(2)
        # with col1:
            # st.write('1-gram')
            # display_wordcloud(ngrams['onegram'])
        # with col2:
            # st.write('2-gram')
            # display_wordcloud(ngrams['twogram'])

        selected_df = reviews_df[selected_restaurant]
        selected_df['DateOfReview'] = pd.to_datetime(selected_df['DateOfReview'], format='%Y-%m-%d')
        selected_df = selected_df.sort_values(by='DateOfReview', ascending=False)
        selected_df['StarRating'] = pd.to_numeric(selected_df['StarRating'])
        selected_df['month_year'] = selected_df['DateOfReview'].dt.to_period('M').dt.to_timestamp().dt.strftime('%b-%Y')
        selected_df['DateOfReview'] = selected_df['DateOfReview'].dt.date
        selected_df = selected_df.reset_index(drop=True)
        filtered_df = display_charts(selected_df)

        analyze_review_button = st.button(':green[Generate AI Summary of Review]')
        
        if analyze_review_button:
            analyze_reviews(selected_restaurant, selected_df[['ReviewDescription', 'StarRating']])
            restaurant_names, reviews_df, summary_dict, ngrams_dict, last_modified_dict = load_and_process_data(bucket_name, json_file_name, bypass_cache=True)
        
        summary = summary_dict[selected_restaurant]['summary']
        pros = summary_dict[selected_restaurant]['pros']
        cons = summary_dict[selected_restaurant]['cons']

        logger.info(f"Summary: {summary}")
        logger.info(f"Pros: {pros}")
        logger.info(f"Cons: {cons}")

        st.subheader("Summary of Reviews")
        last_modified_summary = last_modified_dict[selected_restaurant]['summary']
        last_modified_summary = 'NA' if last_modified_summary == '' else last_modified_summary
        st.write(f'Last fetched date: {last_modified_summary}')
        st.write(summary)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"What they like about {selected_restaurant}:")
            st.write(pros)
        with col2:
            st.subheader(f"What they dislike about {selected_restaurant}:")
            st.write(cons)
        
        display_reviews_df(filtered_df)

if __name__ == "__main__":
    main()
