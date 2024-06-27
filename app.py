import pandas as pd
import streamlit as st
import altair as alt

# Display in wide mode
st.set_page_config(layout="wide")
##################### Read Data #####################
batch = True
if batch:
    # Load the CSV file into a DataFrame
    csv_file_path = 'data/merged1.csv'  # Replace with the actual path to your CSV file
else:
    # Load the CSV file into a DataFrame
    csv_file_path = 'data/Hong Shi Chicken Rice.csv'  # Replace with the actual path to your CSV file

df = pd.read_csv(csv_file_path)

if 'Source' in df.columns:
    df = df[[
        'Source','star_rating', 'date_of_review','review_description'
    ]]
else:
    df = df[[
        'star_rating', 'date_of_review','review_description'
    ]]

# Convert 'date_of_review' to datetime format with the correct format
df['date_of_review'] = pd.to_datetime(df['date_of_review'], format='%Y-%m-%d')
df = df.sort_values(by='date_of_review', ascending=False)

# Create a new column for the month and year
df['month_year'] = df['date_of_review'].dt.to_period('M').dt.to_timestamp().dt.strftime('%b-%Y')
df['date_of_review'] = df['date_of_review'].dt.date

##################### Sidebar #####################
# Add a sidebar with a dropdown list to choose the restaurant
restaurant_names = df['Source'].unique()
selected_restaurant = st.sidebar.selectbox('Select a restaurant:', restaurant_names)

# Filter the DataFrame for the selected restaurant
selected_df = df[df['Source'] == selected_restaurant]
selected_df = selected_df.reset_index(drop=True)

col1, col2 = st.columns(2)
with col1:
    show_empty_reviews = st.checkbox('Include reviews with no description', True)
with col2:
    # Count the number of empty and non-empty reviews
    empty_reviews_count = (selected_df['review_description'] == 'No description provided').sum()
    non_empty_reviews_count = len(selected_df) - empty_reviews_count

    if show_empty_reviews:
        filtered_df = selected_df
        st.write(f"Displaying {selected_df.shape[0]} Total Reviews ({empty_reviews_count} with no description)")
    else:
        filtered_df = selected_df[selected_df['review_description'] != 'No description provided']
        st.write(f"Displaying {len(filtered_df)} reviews")
##################### Bar Chart #####################
# Group by 'star_rating' and count the occurrences
grouped = filtered_df.groupby('star_rating').size().reset_index(name='Count')

# Calculate the average star rating
average_rating = round(filtered_df['star_rating'].mean(),2)

# Create the bar chart using Altair
chart = alt.Chart(grouped).mark_bar().encode(
    x=alt.X('star_rating:N', title='Star Rating', axis=alt.Axis(labelAngle=0)),
    y=alt.Y('Count:Q', title='Count'),
).properties(
    width=600,
    height=200
)


##################### Time Series Line Chart #####################
# Group by 'month_year' and calculate the average star rating for each month
monthly_avg = round(filtered_df.groupby('month_year')['star_rating'].mean().reset_index(),2)

# Create the line chart using Altair with tooltips and point markers
line_chart = alt.Chart(monthly_avg).mark_line(point=True).encode(
    x=alt.X('month_year:T', title='Month/Year'),
    y=alt.Y('star_rating:Q', title='Average Star Rating'),
    tooltip=['month_year:T', 'star_rating:Q']
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
        filtered_df[['month_year', 'review_description', 'star_rating']],
        column_config={
            'month_year': st.column_config.TextColumn(
                "Review Date",
                help="Date when the review was posted",
                width="small"
            ),
            'star_rating': st.column_config.NumberColumn(
                "Star Rating",
                help="Rating given by the reviewer",
                format="%d",
                width="small"
            ),
            'review_description': st.column_config.TextColumn(
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
        filtered_df[['month_year', 'review_description', 'star_rating']],
        column_config={
            'month_year': st.column_config.TextColumn(
                "Review Date",
                help="Date when the review was posted",
                width="small"
            ),
            'star_rating': st.column_config.NumberColumn(
                "Star Rating",
                help="Rating given by the reviewer",
                format="%d",
                width="small"
            ),
            'review_description': st.column_config.TextColumn(
                "Review Description",
                help="Full description of review",
                width="large"
            )
        },
        use_container_width=True
    )
