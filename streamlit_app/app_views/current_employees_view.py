# All necessary imports

import streamlit as st
from datetime import datetime
import time
from streamlit_app.main_functions import (
    query_current_employees_table,
    get_current_employees_db, 
    parse_duration
)

# Basic logging configuration 

import logging
logger = logging.getLogger('stealthscout')

# Defining All Relevant Functions
# 1. Getting List of Companies in Current Employee Table - get_cached_current_companies
# 2. Display Profile Card and Time Since Last Update - display_profile_card, parse_duration
# 3. Form to Capture Search Interest - st.form(key="search_form")
# 4. Button to Search the Current Employees Table - search_submitted
# 5. Current Employee Table-related Functions from Main Functions - query_current_employees_table, get_current_employees_db
# 6. Parent Function executing View - current_employee_search_view
# ------------------------------


def current_employee_search_view(supabase_client):
    
    @st.cache_data(ttl=30)
    def get_cached_current_companies(_supabase_client):
        """
        Cached wrapper for current_company data fetch.
        Reduces database calls and improves performance.
        """
        logger.info("Cache miss - fetching companies from database")
        list_of_retrieved_companies = get_current_employees_db(supabase_client)
        number_of_retrieved_companies = len(list_of_retrieved_companies)
        logger.info(f"Cached companies list has {len(list_of_retrieved_companies)} companies.")
        return list_of_retrieved_companies, number_of_retrieved_companies
    
    logger.info("Current Employees Search View accessed.")
    logger.info("Getting list_of_current_companies from db/cache.")
    list_of_current_companies, number_of_current_companies = get_cached_current_companies(supabase_client)
    logger.info(f"Retrieved {number_of_current_companies} companies from cache.")


    # ------------------------------
    

    #Function to display the profile cards
    def display_profile_card(profile):

    # Custom CSS for styling
        st.markdown("""
        <style>
        .profile-container {
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        background-color: #ffffff;
        }
        .profile-container h3 {
            color: #2c3e50;
            margin: 0 0 0.5rem 0;
            font-size: 1.6rem;
            font-weight: 600;
        }
        .profile-container h4 {
            color: #34495e;
            margin: 1.5rem 0 0.5rem 0;
            font-size: 1.3rem;
            font-weight: 600;
        }
        .profile-container p {
            margin: 0 0 0.8rem 0;
            font-size: 0.95rem;
            line-height: 1.5;
            color: #555;
        }
        .profile-container ul {
            margin: 0 0 1rem 0;
            padding-left: 1.2rem;
        }
        .profile-container li {
        margin-bottom: 0.6rem;
        font-size: 0.9rem;
        line-height: 1.4;
        color: #555;
        }
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        .profile-name {
            margin: 0;
            font-size: 1.6rem;
            font-weight: 600;
            color: #2c3e50;
        }
            .label-container {
            margin-bottom: 0.8rem;
        }
        .label {
        display: inline-block;
        padding: 0.3em 0.6em;
        font-size: 0.7rem;
        font-weight: 600;
        color: #000000;  /* Default text color, will be overridden */
        border-radius: 50px;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
        border: 2px solid;
        background-color: transparent;  /* Will be overridden */
    }

    /* Role Label */
    .label-role {
        border-color: #2C3E50;  /* Dark Blue */
        color: #2C3E50;
    }

    /* Senior Operator Label */
    .label-senior {
        border-color: #00246B;  /* Very Dark Blue */
        color: #00246B;
    }

    /* Repeat Founder Label */
    .label-repeat {
        border-color: #735DA5;  /* Dark Golden Brown */
        color: #735DA5;
    }

    /* Status Low Confidence Label */
    .label-status-low {
        border-radius: 0px;  /* No border radius */
        border-color: #e04c16;  
        color: #FFFFFF;  /* White text */
        background-color: #e04c16;
    }

    /* Status High Confidence Label */
    .label-status-high {
        border-radius: 0px;  /* No border radius */
        border-color: #2C5F2D;  /* Dark Green */
        color: #FFFFFF;  /* White text */
        background-color: #2C5F2D;
    }

                
        .profile-container a {
            color: #3498db;
            text-decoration: none;
            transition: color 0.2s ease;
        }
        .profile-container a:hover {
        color: #2980b9;
        text-decoration: underline;
        }
        .more-info {
            font-style: italic;
            color: #7f8c8d;
            font-size: 0.85rem;
        }
        .profile-divider {
            border-top: 1px solid #e0e0e0;
            margin: 1rem 0;
        }

        .timestamp {
            font-size: 0.8rem;
            color: #666;
            margin-top: 0.2rem;
            margin-bottom: 1rem;
            display: block;
        }
        .profile-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

        # Build the HTML content
        html_content = '<div class="profile-container">'

        # Create header with name and profile status
        html_content += '<div class="header-container">'
        html_content += f"<h3 class='profile-name'>{profile['first_name']} {profile['last_name']}</h3>" 

        # Profile Status Label with confidence labels.
        if profile.get('profile_status'):
            status = profile['profile_status']
            confidence = profile.get('status_confidence_label', 'HIGH').lower()  # Default to HIGH if not set
    
        # Set label class based on confidence
        status_class = f'label-status-{confidence}'
    
        # Set display status
        if status == 'stealth':
            display_status = 'Building in Stealth'
        elif status == 'building_in_public':
            display_status = 'Building in Public'
        elif status == 'recently_quit':
            display_status = 'Recently Quit'
        elif status == 'currently_employed':
            display_status = 'Currently Employed'
        
        html_content += f'<span class="label {status_class}">{display_status}</span>'
        html_content += '</div>'
        # Labels container
        labels_html = '<div class="label-container">'
    
        # Role at company searched
        if 'role_at_current_company' in profile and profile['role_at_current_company']:
            labels_html += f'<span class="label label-role">{profile["role_at_current_company"]}</span>'
    
        # Key labels
        if profile.get('is_senior_operator'):
            labels_html += '<span class="label label-senior">Senior Operator</span>'
        if profile.get('is_repeat_founder'):
            labels_html += '<span class="label label-repeat">Repeat Founder</span>'
        
        labels_html += '</div>'
        html_content += labels_html

        # Location
        if profile.get('location'):
            html_content += f'<p>📍 {profile["location"]}</p>'
        
        # Experience
        html_content += '<h6>Experience</h6><ul>'
        for exp in profile['experience'][:3]:
            html_content += f'<li><strong>{exp["title"]}</strong> at <strong>{exp["company"]}</strong><br><span style="font-size: 0.85rem; color: #7f8c8d;">{exp["date_range"]} ({exp["duration"]})</span></li>'
        html_content += '</ul>'
    
        # Education
        if profile.get('education'):
            html_content += '<h6>Education</h6><ul>'
            for edu in profile['education'][:2]:
                html_content += f'<li><strong>{edu["degree"]}</strong> from {edu["school"]}<br><span style="font-size: 0.85rem; color: #7f8c8d;">{edu["date_range"]}</span></li>'
            html_content += '</ul>'
    
        html_content += '<div class="profile-divider"></div>'
        # Footer container with timestamp and LinkedIn profile link
        html_content += '<div class="profile-footer">'

        # Add last refresh timestamp if available
        if profile.get('last_attempted_refresh_timestamp'):
            try:
                refresh_time = datetime.fromisoformat(profile['last_attempted_refresh_timestamp'].replace('Z', '+00:00'))
                current_time = datetime.now(refresh_time.tzinfo)
                time_ago = current_time - refresh_time
                if time_ago.days > 0:
                    time_str = f"{time_ago.days} days ago"
                elif time_ago.seconds // 3600 > 0:
                    time_str = f"{time_ago.seconds // 3600} hours ago"
                else:
                    time_str = f"{time_ago.seconds // 60} minutes ago"
                html_content += f'<div class="timestamp"><strong>Last updated {time_str}</strong></div>'
            except Exception as e:
                html_content += '<div class="timestamp"></div>'
                logger.error(f"Error processing refresh timestamp: {str(e)}")
                pass
    
        # LinkedIn profile link
        html_content += f'<div><a href="{profile["linkedin_url"]}" target="_blank">View LinkedIn Profile</a></div>'
        
        html_content += '</div>'  # Close profile-footer
        
        # Close the container div
        html_content += '</div>'
        
        # Output the HTML content
        st.markdown(html_content, unsafe_allow_html=True)
    
        # Add spacing between cards
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)



    # ------------------------------



    # Custom CSS for fixed sidebar
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
            position: fixed;
            top: 0;
            height: 100vh;
        }
        </style>
    """, unsafe_allow_html=True)

    # CSS styling for the search form.
    st.markdown(
        """
        <style>
        .section-text {
        color: #2c3e50;  /* Darker color */
        font-size: 0.85em;
        font-weight: 550;  /* Slightly bolder */
        margin-bottom: 0.8em;
        margin-top: 0.5em;
        text-decoration: underline;  /* Add underline */
        text-decoration-thickness: 1px;  /* Make underline thinner */
        text-underline-offset: 4px;  /* Add space between text and underline */
    }
    .form-container {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True
    )


    # ------------------------------


    with st.form(key="search_form"):
        # Multiselect option for choosing past companies
        st.markdown('<div class="section-text">Start with 3 Companies</div>', unsafe_allow_html=True)
        
        past_company_name = st.multiselect(
            "Choose current companies to get started", 
            list_of_current_companies, 
            default=None, 
            help="You can pick up to three companies at once to get started.", 
            max_selections=3, 
            placeholder="Choose upto three companies to get started.", 
            label_visibility="collapsed"
        )

        st.markdown('<div class="section-text">Apply additional filters</div>', unsafe_allow_html=True)
        # Create two columns for companies and filters
        col1, col2 = st.columns([1, 2])
        with col1:
            filter_repeat_founder = st.checkbox("Repeat Founders")
        with col2:
            filter_senior_operator = st.checkbox("Senior Operators")
    
        # Add a submit button to the form
        search_submitted = st.form_submit_button("Search Profiles", type='primary')
    
        # Log form inputs
        if search_submitted:
            if not past_company_name:
                st.warning("Please select at least one company to search.")
                st.stop()  # Stop execution here
        
            logger.info(f"User selected {len(past_company_name)} companies for search: {past_company_name}")
            logger.info(f"Additional filters - Repeat Founders: {filter_repeat_founder}, Senior Operators: {filter_senior_operator}")

    # Get the past company URL (example: Freshworks)
    linkedin_profile_list = []
    total_linkedin_profiles_found = 0

    # Button to trigger search
    if search_submitted:
        start_time = time.time()
        logger.info("Search button pressed by user.")

        with st.spinner("Searching for profiles..."):
        
            for company_name in past_company_name:
                list_of_profiles_retrieved = query_current_employees_table(
                    supabase_client, 
                    company_name,
                    filter_repeat_founder, 
                    filter_senior_operator)
                if len(list_of_profiles_retrieved):
                    linkedin_profile_list.extend(list_of_profiles_retrieved)
                    time.sleep(0.7)
                    st.success(f"Profiles found for company {company_name}")
                else:
                    time.sleep(0.7)
                    st.warning(f"No profiles found or an error occurred for company {company_name}.")
            logger.info(f"Search process completed in {time.time() - start_time} seconds.")
            st.markdown(f'<div class="section-text">Found {len(linkedin_profile_list)} profiles.</div>', unsafe_allow_html=True)
            logger.info(f"Search completed. Total profiles found: {len(linkedin_profile_list)}")
        if len(linkedin_profile_list):
            linkedin_profile_list.sort(key=lambda profile: parse_duration(profile['experience'][0]['duration']))
            for profile in linkedin_profile_list:
                # Sort the profiles based on the duration of the most recent experience
                display_profile_card(profile)
    
            logger.info(f"Displaying {len(linkedin_profile_list)} profiles to user.")