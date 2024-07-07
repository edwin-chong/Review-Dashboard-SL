import boto3
import json
import pandas as pd
import streamlit as st
import requests
import altair as alt
from st_keyup import st_keyup
from streamlit_autorefresh import st_autorefresh
from functools import lru_cache

# Initialize the S3 client
s3 = boto3.client('s3')

# Define the bucket name and the file name
bucket_name = st.secrets["S3_BUCKET_NAME"]
json_file_name = st.secrets["S3_JSON_NAME"]

@st.cache_data(ttl=3600)  # Cache the processed data for 1 hour
def load_and_process_data(bucket_name, json_file_name):
    response = s3.get_object(Bucket=bucket_name, Key=json_file_name)
    json_data = response['Body'].read().decode('utf-8')
    data = json.loads(json_data)
    processed_data = {}
    for restaurant, reviews in data.items():
        df = pd.DataFrame(reviews)
        df['DateOfReview'] = pd.to_datetime(df['DateOfReview'], format='%Y-%m-%d')
        df = df.sort_values(by='DateOfReview', ascending=False)
        df['StarRating'] = pd.to_numeric(df['StarRating'])
        df['month_year'] = df['DateOfReview'].dt.to_period('M').dt.to_timestamp().dt.strftime('%b-%Y')
        df['DateOfReview'] = df['DateOfReview'].dt.date
        processed_data[restaurant] = df.reset_index(drop=True)
    return list(data.keys()), processed_data

# Function to handle the status polling
def poll_status():
    if st.session_state.request_id:
        status_url = f'{base_url}/status/{st.session_state.request_id}'
        response = requests.get(status_url)
        status = response.json().get('status')
        st.session_state.status = status

def send_scraping_request(res_name, loc_name, review_limit):
    url = f'{base_url}/scrape'
    data = {
        'business_name': f'{res_name} - {loc_name}',
        'sort_order': 'Newest',
        'review_limit': review_limit
    }
    response = requests.post(url, json=data)
    request_id = response.json().get('request_id')
    return request_id

# Display in wide mode
st.set_page_config(layout="wide")
base_url= st.secrets["FLASK_APP_URL"]


##################### Sidebar #####################
# Sidebar with search bar and dropdown
st.sidebar.header('Restaurant Selection')
# restaurant_names = get_restaurant_names()
restaurant_names, data = load_and_process_data(bucket_name, json_file_name)

# Create a container in the sidebar for keyup functionality
with st.sidebar:
    # Text input for searching in the sidebar
    search_term = st_keyup("Enter a value", key="0")

    # Update session state with the search term
    st.session_state.search_term = search_term

# Initialize session state variables
if 'filtered_restaurant_names' not in st.session_state:
    st.session_state.filtered_restaurant_names = restaurant_names
if 'request_id' not in st.session_state:
    st.session_state.request_id = None
if 'request_res' not in st.session_state:
    st.session_state.request_res = None
if 'status' not in st.session_state:
    st.session_state.status = None

# Dropdown list with filtered restaurant names
selected_restaurant = st.sidebar.selectbox('Select a restaurant:', st.session_state.filtered_restaurant_names)

# Update the filtered restaurant names based on the search term
if st.session_state.search_term:
    st.session_state.filtered_restaurant_names = [name for name in restaurant_names if st.session_state.search_term.lower() in name.lower()]
else:
    st.session_state.filtered_restaurant_names = restaurant_names 


##################### Injected Javascript #####################
# JavaScript to periodically poll for status updates
polling_js = """
<script>
function pollStatus() {
    fetch('/poll_status').then(response => response.json()).then(data => {
        if (data.status === 'Completed') {
            Streamlit.setComponentValue({status: 'Completed'});
        } else if (data.status.includes('Failed')) {
            Streamlit.setComponentValue({status: data.status});
        } else {
            setTimeout(pollStatus, 80);
        }
    });
}
setTimeout(pollStatus, 80);
</script>
"""
# Inject the JavaScript into the Streamlit app
st.markdown(polling_js, unsafe_allow_html=True)
# Auto poll on intervals
if st.session_state.request_id:
    st_autorefresh(interval=80, key="poll_status")
    print('Check status')
    poll_status()
################################################################


##################### Main Content #####################
# Display the selected restaurant
st.subheader(f'Selected Restaurant: :green[{selected_restaurant}]')
if selected_restaurant not in restaurant_names:
    st.sidebar.subheader(':red[Restaurant not found!]')
    st.sidebar.write('Please try a different name. If the restaurant is not found in the list, you can request for it. (Will take a few minutes depending on the number of reviews)')

    res_name = st.sidebar.text_input('Name of restaurant')
    loc_name = st.sidebar.text_input('Location/Branch?')
    review_limit = st.sidebar.number_input('Maximum no. of reviews to fetch:', min_value=1, value=100, step=1)

    generate_new_data = st.sidebar.button('Generate new data')
    if generate_new_data:
        st.session_state.res_name = res_name
        st.session_state.request_id = send_scraping_request(res_name, loc_name, review_limit)
        st.session_state.status = 'In Progress'

    selected_df = pd.DataFrame(columns=['DateOfReview', 'StarRating', 'month_year', 'ReviewDescription'])
else:
    selected_df = data[selected_restaurant]
    # Format df columns
    selected_df['DateOfReview'] = pd.to_datetime(selected_df['DateOfReview'], format='%Y-%m-%d')
    selected_df = selected_df.sort_values(by='DateOfReview', ascending=False)
    selected_df['StarRating'] = pd.to_numeric(selected_df['StarRating'])
    selected_df['month_year'] = selected_df['DateOfReview'].dt.to_period('M').dt.to_timestamp().dt.strftime('%b-%Y')
    selected_df['DateOfReview'] = selected_df['DateOfReview'].dt.date
    selected_df = selected_df.reset_index(drop=True)


# # Display status updates
# if st.session_state.status:
#     if st.session_state.status == 'Completed':
#         st.toast(f':large_green_circle: Scraping request for {st.session_state.res_name} has completed, please refresh page!')
#         st.session_state.request_id = None
#         st.session_state.status = None
#     elif 'Failed' in st.session_state.status:
#         st.toast(f':large_orange_circle: Scraping request for {st.session_state.res_name} has failed. Please try again with a different name')
#         st.session_state.request_id = None
#         st.session_state.status = None
#     elif 'In Progress' in st.session_state.status:
#         st.toast(f':large_yellow_circle: Scraping request for {st.session_state.res_name} sent! Please check back later!')

col1, col2 = st.columns(2)
with col1:
    show_empty_reviews = st.checkbox('Include reviews with no description', True)
with col2:
    # Count the number of empty and non-empty reviews
    empty_reviews_count = (selected_df['ReviewDescription'] == 'No description provided').sum()
    non_empty_reviews_count = len(selected_df) - empty_reviews_count

    if show_empty_reviews:
        filtered_df = selected_df
        st.write(f"Displaying {selected_df.shape[0]} Total Reviews ({empty_reviews_count} with no description)")
    else:
        filtered_df = selected_df[selected_df['ReviewDescription'] != 'No description provided']
        st.write(f"Displaying {len(filtered_df)} reviews")

##################### Bar Chart #####################
# Group by 'StarRating' and count the occurrences
ratingGroupedDf = filtered_df.groupby('StarRating').size().reset_index(name='Count')

# Calculate the average star rating
average_rating = round(filtered_df['StarRating'].mean(),2)

# Create the bar chart using Altair
chart = alt.Chart(ratingGroupedDf).mark_bar().encode(
    x=alt.X('StarRating:N', title='Star Rating', axis=alt.Axis(labelAngle=0)),
    y=alt.Y('Count:Q', title='Count'),
).properties(
    width=600,
    height=200
)


##################### Time Series Line Chart #####################
# Group by 'month_year' and calculate the average star rating and count for each month
monthlyGroupedDf = filtered_df.groupby('month_year')['StarRating'].agg(['mean', 'count']).reset_index()
monthlyGroupedDf.columns = ['Date', 'Star Rating', 'Num_Reviews']

# Round the StarRating to 2 decimal places
monthlyGroupedDf['Star Rating'] = round(monthlyGroupedDf['Star Rating'], 2)
print(monthlyGroupedDf.head(5))

# Create the line chart using Altair with tooltips and point markers
line_chart = alt.Chart(monthlyGroupedDf).mark_line(point=True).encode(
    x=alt.X('Date:T', title='Date [Month]'),
    y=alt.Y('Star Rating:Q', title='Average Star Rating'),
    tooltip=['Date:T', 'Star Rating:Q', 'Num_Reviews:Q']
).properties(
    width=600,
    height=200
)

# .interactive()

##################### Display Charts Side by Side #####################
col1, col2 = st.columns(2)

with col1:
    st.subheader('Average Star Rating Over Time')
    st.altair_chart(line_chart, use_container_width=True)

with col2:
    st.subheader(f'Average Star Rating: {average_rating:.2f} ★')
    st.altair_chart(chart, use_container_width=True)

# # Add instructions for interactivity
# st.markdown("""
# * **Drag** to move the chart
# * **Scroll** to zoom in and out
# * **Double-click** to reset the chart scale
# """)
# st.altair_chart(line_chart, use_container_width=True)


##################### Reviews Table #####################
st.title('Reviews')
st.markdown("""
Tips:
* Double click to see the full description of each rating
""")

adjustable_table = st.checkbox('Adjustable table')
if adjustable_table:
    values = st.slider(
        "Slide to adjust width of dataframe",
        200, 1000, 600
    )

filtered_df = filtered_df.reset_index(drop=True)

if adjustable_table:
    st.dataframe(
        filtered_df[['month_year', 'ReviewDescription', 'StarRating']],
        column_config={
            'month_year': st.column_config.TextColumn(
                "Review Date",
                help="Date when the review was posted",
                width="small"
            ),
            'StarRating': st.column_config.NumberColumn(
                "Star Rating",
                help="Rating given by the reviewer",
                format="%d",
                width="small"
            ),
            'ReviewDescription': st.column_config.TextColumn(
                "Review Description",
                help="Full description of review",
                width="large"
            )
        },
        use_container_width=False,
        width=values
    )
else:
    st.dataframe(
        filtered_df[['month_year', 'ReviewDescription', 'StarRating']],
        column_config={
            'month_year': st.column_config.TextColumn(
                "Review Date",
                help="Date when the review was posted",
                width="small"
            ),
            'StarRating': st.column_config.NumberColumn(
                "Star Rating",
                help="Rating given by the reviewer",
                format="%d",
                width="small"
            ),
            'ReviewDescription': st.column_config.TextColumn(
                "Review Description",
                help="Full description of review",
                width="large"
            )
        },
        use_container_width=True
    )
