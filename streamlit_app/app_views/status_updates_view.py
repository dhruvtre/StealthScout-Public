# All necessary imports

import streamlit as st
import pandas as pd
from typing import List, Dict
from datetime import datetime, timedelta

# Basic logging configuration 

import logging
logger = logging.getLogger('stealthscout')

# Defining All Relevant Functions
# 1. Get Complete Profile Details for Each URL w Update - get_profile_details
# 2. Get all Status Updates from DB - get_status_updates
# 3. Display Profile Card and Time Since Last Update - display_status_update
# 4. Parent Function executing View - status_updates_view
# ------------------------------

def status_updates_view(supabase_client):

    """Main status updates view function"""

    # status_updates_view.py
    @st.cache_data(ttl=1800)  # 1 hour cache
    def get_profile_details(_supabase_client, profile_id = '', linkedin_url = '') -> Dict:

        """Get full_name and search_company for a profile"""

        if profile_id:
            try:
                logger.info(f"Fetching profile details for profile ID: {profile_id}")
                response = supabase_client.table("Unicorn-Stealth-Founder-Profiles")\
                    .select("full_name, search_company")\
                    .eq("id", profile_id)\
                    .single()\
                    .execute()
            except Exception as e:
                logger.info(f"Error fetching profile details: {str(e)}")
                return {}
            return response.data
        else:
            try:
                logger.info(f"Fetching profile details for Profile with Linkedin Url: {linkedin_url}")
                response = supabase_client.table("Current-Employee-Profiles")\
                    .select("full_name, current_company")\
                    .eq("linkedin_url", linkedin_url)\
                    .single()\
                    .execute()
            except Exception as e:
                logger.info(f"Error fetching profile details: {str(e)}")
                return {}
            return response.data
    

    # ------------------------------


    @st.cache_data(ttl=1800)  # 1 hour cache
    def get_status_updates(_supabase_client) -> List[Dict]:

        """Get status updates from last 3 months"""
        
        try:
            three_months_ago = (datetime.now() - timedelta(days=90)).isoformat()
            logger.info(f"Fetching status updates since: {three_months_ago}")
            # Query the status updates table
            response = supabase_client.table("stealth_founder_status_update_table")\
            .select("*")\
            .gte("timestamp", three_months_ago)\
            .neq("new_status", "currently_employed")\
            .order("timestamp", desc=True)\
            .execute()
            logger.info(f"Found {len(response.data)} status updates.")
        
            # Debug info
            
            return response.data if response.data else []
        
        except Exception as e:
            logger.info(f"Error fetching status updates: {e}")
            return []


    # ------------------------------


    def display_status_update(supabase_client, update: Dict):

        """Enter Docstring"""

        # Get profile details first
        if update['profile_id']:
            update_identifier = update['profile_id']
            company_param = 'search_company'
            table = 'stealth_founders'
        else:
            update_identifier = update['linkedin_url']
            company_param = 'current_company'
            table = 'current_employees'
        try:
            logger.info(f"Displaying status update for {update_identifier}")
            if table == 'stealth_founders':
                profile = get_profile_details(supabase_client, profile_id = update_identifier)
            elif table == 'current_employees':
                profile = get_profile_details(supabase_client, linkedin_url = update_identifier)
            company_to_show = profile[company_param]
            # Calculate time ago
            time_str = "Recently"  # default value
            if update.get('timestamp'):
                try:
                    update_time = datetime.fromisoformat(update['timestamp'].replace('Z', '+00:00'))
                    current_time = datetime.now(update_time.tzinfo)
                    time_ago = current_time - update_time
                
                    if time_ago.days > 0:
                        time_str = f"{time_ago.days} days ago"
                    elif time_ago.seconds // 3600 > 0:
                        time_str = f"{time_ago.seconds // 3600} hours ago"
                    else:
                        time_str = f"{time_ago.seconds // 60} minutes ago"
                except Exception as e:
                    logger.error(f"Error processing timestamp: {str(e)}")
            
        except Exception as e:
             logger.error(f"Error displaying status update for {update_identifier}: {e}")
        
        
        st.markdown("""
        <style>
        .status-card {
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            background-color: #ffffff;
        }
        .timestamp {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 0.7rem;
        }
        .profile-footer {
        display: flex;
        justify-content: space-between;
        align-items: end;
        margin-top: 1rem;
        }
        .label-old-status, .label-new-status {
            display: inline-block;
            padding: 0.2em 0.5em;
            font-size: 0.8rem;
            font-weight: 600;
            color: #000;
            border-radius: 50px;
            margin: 0 0.3em;
            border: 1px solid #ccc;
            background-color: #f5f5f5;
            vertical-align: middle;
        }

        .label-old-status {
            border-color: #666;
            color: #666;  
            background-color: #eaeaea; /* A neutral gray for old status */
        }

        .label-new-status {
            border-color: #2C5F2D;
            color: #2C5F2D;  
            background-color: #e5f1e5; /* A light green tone for new status */
        }

        .arrow {
            display: inline-block;
            margin: 0 0.0em;
            color: #888; /* Slightly darker gray */
            font-weight: bold;
            font-size: 1rem;
            vertical-align: middle;
        }
                    .status-text-first {
            font-size: 1.05em;
            font-weight: 600; 
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown(
        f"""<div class="status-card">
            <div class="timestamp">Last updated {time_str}</div>
            <p class="status-text">
                <p class="status-text-first">
                {profile['full_name']}, ex-employee at {company_to_show}, moved from 
                <span class="label-old-status">{update['old_status']}</span> 
                <span class="arrow">→</span> 
                <span class="label-new-status">{update['new_status']}</span>
                </p>
            </p>
            <p class="status-text">
            <strong>Previously:</strong> {update['prev_role']['title']} at {update['prev_role']['company']}<br /> 
            <strong>Now:</strong> {update['curr_role']['title']} at {update['curr_role']['company']}
            </p>
            <div class = "profile-footer">
                <span><a class="view-profile" href="{update['linkedin_url']}" target="_blank">View Profile</a></span>
            </div>
        </div>""",
        unsafe_allow_html=True
        )


    # ------------------------------


    st.markdown("### Recent Status Changes")
    updates = get_status_updates(supabase_client)
    logger.info(f"Number of status updates fetched: {len(updates)}")
    
    if not updates:
            st.info("No recent status updates found.")
            logger.info("No recent status updates found.")
            
            return
    logger.info("Rendering status updates view.")    
    for update in updates:
            
            display_status_update(supabase_client, update)

    # Log the number of updates displayed
    logger.info(f"Number of status updates displayed: {len(updates)}")      
