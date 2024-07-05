import streamlit as st

for key in st.session_state.keys():
    del st.session_state[key]