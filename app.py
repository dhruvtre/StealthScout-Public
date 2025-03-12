# All necessary imports

import streamlit as st
from streamlit_app.app_views.stealth_founders_view import search_db_view 
from streamlit_app.app_views.status_updates_view import status_updates_view 
from streamlit_app.app_views.current_employees_view import current_employee_search_view 
from streamlit_app.main_functions import *

# Basic logging configuration 

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('stealthscout')

# Load environment variables from the correct path

import os
from dotenv import load_dotenv
load_dotenv()

supabase_url = os.getenv("supabase_url")
supabase_key = os.getenv("supabase_key")

# Setting up the supabase client

supabase_client = create_supabase_client(supabase_url, supabase_key)

# Defining All Relevant Functions
# 1. get_cached_companies
# 2. st.sidebar
# 3. Page Rerouting - status_updates_view, search_db_view, current_employee_search_view
# ------------------------------

#Function to cache list of companies retrieved from db
@st.cache_data(ttl=3600)
def get_cached_companies(_supabase_client):
        """
        Cached wrapper for company data fetch.
        Reduces database calls and improves performance.
        """
        logger.info("Cache miss - fetching companies from database")
        list_of_retrieved_companies = get_companies_from_db(supabase_client)
        number_of_retrieved_companies = len(list_of_retrieved_companies)
        logger.info(f"Cached companies list has {len(list_of_retrieved_companies)} companies")
        return list_of_retrieved_companies, number_of_retrieved_companies


# ------------------------------


list_of_search_companies, number_of_search_companies = get_cached_companies(supabase_client)
number_of_stealth_linkedin_urls = count_stealth_profiles_with_urls(supabase_client)
number_of_current_linkedin_urls = count_current_profiles_with_urls(supabase_client)

with st.sidebar:
    st.image(".streamlit/ss_logo.png", width=200) 

    st.markdown('''---''')

    st.markdown(f''':red-background[**Unique Companies**]: {number_of_search_companies}''')
    st.markdown(f''':red-background[**Stealth Profiles**]: {number_of_stealth_linkedin_urls}''')
    st.markdown(f''':red-background[**Current Employees**]: {number_of_current_linkedin_urls}''')
    pages = {
    "**Search Database**": "Find Potential Founders",
    "**Recent Status Updates**": "Track Founder Movements", 
    "**Current Employee Search**": "Search for Current Employees",
}
    st.markdown("""
<style>
div.row-widget.stRadio > div {
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)
    
    page = st.sidebar.radio(
        "View Selection",  # Non-empty label
        list(pages.keys()),
        label_visibility="collapsed",
        index=0
    )
            

# ------------------------------


# Update routing
if page == "**Recent Status Updates**":
    logger.info("User clicked to view recent status updates.")
    status_updates_view(supabase_client)
elif page == "**Current Employee Search**":
     logger.info("User clicked to search for current employees.")
     current_employee_search_view(supabase_client)
else:
    logger.info("User clicked to search the database.")
    search_db_view(supabase_client, list_of_search_companies)