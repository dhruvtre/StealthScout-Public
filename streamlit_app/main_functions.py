# All necessary imports

from typing import List, Dict
import re

# Basic logging configuration 

import logging
logger = logging.getLogger('stealthscout')

# Initialize Supabase client

from supabase import create_client, Client
def create_supabase_client(supabase_url, supabase_key):
    supabase: Client = create_client(supabase_url, supabase_key)
    return supabase

# Defining All Relevant Functions
# 1. get_companies_from_db
# 2. query_stealth_founder_table
# 3. parse_duration
# 4. count_stealth_profiles_with_urls
# 5. count_current_profiles_with_urls
# 6. query_current_employees_table
# 7. get_current_employees_db
# ------------------------------


def get_companies_from_db(supabase_client) -> List[str]:

    """
    Fetch unique company names from the 'search_company' column of the 
    'Unicorn-Stealth-Founder-Profiles' table for dropdown selection.
    
    Args:
        supabase_client: An initialized and authenticated Supabase client.
        
    Returns:
        A list of unique company names present in the 'search_company' column.
        Returns an empty list if no companies are found or an error occurs.
    """
    
    try:
        logger.info("Attempting to fetch unique search_company names from profiles table")
        
        # Step 1: Fetch all non-null and non-empty search_company entries
        response = supabase_client.table("Unicorn-Stealth-Founder-Profiles")\
            .select("search_company")\
            .neq("search_company", None)\
            .neq("search_company", "")\
            .execute()
        
        if not response.data:
            logger.warning("No search_company entries found in Unicorn-Stealth-Founder-Profiles table")
            return []
        
        # Step 2: Extract company names and normalize them
        search_companies = [record["search_company"].strip() for record in response.data if record.get("search_company")]
        logger.info(f"Retrieved {len(search_companies)} search_company entries from profiles table")
        
        # Step 3: Deduplicate the company names
        unique_search_companies = sorted(list(set(search_companies)))
        logger.info(f"Unique search_company entries count: {len(unique_search_companies)}")
        
        return unique_search_companies
    
    except Exception as e:
        logger.error(f"Error fetching companies: {str(e)}", exc_info=True)
        return []


# ------------------------------


def query_stealth_founder_table(supabase, past_company, profile_statuses=None, filter_repeat_founder=False, filter_senior_operator=False):
    """
    Query the Supabase table with filtering options.
    
    Args:
        supabase: Supabase client
        past_company: Company name to search for
        profile_statuses: List of profile statuses to filter by
        filter_repeat_founder: Boolean to filter for repeat founders
        filter_senior_operator: Boolean to filter for senior operators
    """
    try:
        # Start with base query
        query = supabase.table("Unicorn-Stealth-Founder-Profiles")\
            .select("*")\
            .eq("search_company", past_company)
        
        # Add profile status filter if provided
        if profile_statuses and len(profile_statuses) > 0:
            # Convert to lowercase for DB matching
            statuses = [status.lower().replace(" ", "_") for status in profile_statuses]
            # Add OR condition for all selected statuses
            query = query.in_("profile_status", statuses)
        else:
            # Exclude profiles with empty or NULL profile_status
            query = query.neq("profile_status", "").neq("profile_status", "currently_employed")\

        # Add conditional filters
        if filter_repeat_founder:
            query = query.eq("is_repeat_founder", True)
        
        if filter_senior_operator:
            query = query.eq("is_senior_operator", True)

        # Execute query
        response = query.execute()
        
        # Process response
        if response.data and len(response.data) > 0:
            logger.info(f"Successfully retrieved profiles for {past_company}")
            logger.info(f"Profile statuses filtered: {profile_statuses if profile_statuses else 'None'}")
            logger.info(f"Additional filters - Repeat Founder: {filter_repeat_founder}, Senior Operator: {filter_senior_operator}")
            logger.info(f"Found {len(response.data)} matching profiles")
            return response.data
        else:
            # Build filter message for logging
            filter_msg = []
            if profile_statuses:
                filter_msg.append(f"Status: {', '.join(profile_statuses)}")
            if filter_repeat_founder:
                filter_msg.append("Repeat Founders")
            if filter_senior_operator:
                filter_msg.append("Senior Operators")
            
            filter_str = f" with filters ({', '.join(filter_msg)})" if filter_msg else ""
            logger.warning(f"No profiles found for {past_company}{filter_str}")
            return []

    except Exception as e:
        logger.error(f"Error querying profiles for {past_company}: {str(e)}")
        return []


# ------------------------------


def parse_duration(duration_string):
    """
    Parses a duration string and calculates the total number of months.
    
    Supported formats:
    - "__ yr"
    - "__ yrs"
    - "__ mo"
    - "__ mos"
    - "__ yr __ mo"
    - "__ yr __ mos"
    - "___ yrs _ mo"
    - "___ yrs __ mos"
    
    Args:
        duration_string (str): The duration string to parse.
        
    Returns:
        int: Total number of months.
    """
    total_months = 0
    
    # Define the regex pattern to capture years and months
    # This pattern captures:
    # - (\d+): One or more digits
    # - \s*: Optional whitespace
    # - (yr|yrs|mo|mos): The unit (year/years/month/months)
    pattern = re.compile(r'(\d+)\s*(yr|yrs|mo|mos)', re.IGNORECASE)
    
    # Find all matches in the duration string
    matches = pattern.findall(duration_string)
    
    for match in matches:
        number, unit = match
        number = int(number)
        unit = unit.lower()
        
        if unit.startswith('yr'):
            total_months += number * 12
        elif unit.startswith('mo'):
            total_months += number
    
    return total_months


# ------------------------------


def count_stealth_profiles_with_urls(supabase_client):
    """
    Counts the number of unique LinkedIn URLs in the Unicorn-Stealth-Founder-Profiles table.
    
    Args:
        supabase_client: An initialized and authenticated Supabase client.
        
    Returns:
        The number of unique LinkedIn URLs as an integer.
        Returns None if an error occurs during the query.
    """
    try:
        logger.info("Attempting to count unique LinkedIn URLs in Unicorn-Stealth-Founder-Profiles table")
        
        # Step 1: Query for distinct LinkedIn URLs, excluding NULL and empty strings
        response = supabase_client.table("Unicorn-Stealth-Founder-Profiles")\
            .select("linkedin_url")\
            .neq("linkedin_url", None)\
            .neq("linkedin_url", "")\
            .neq("profile_status", "")\
            .execute()
        
        # Step 2: Check if data is returned
        if response.data:
            # Extract 'linkedin_url' from each record and add to a set for uniqueness
            unique_linkedin_urls = set()
            for record in response.data:
                linkedin_url = record.get("linkedin_url")
                if linkedin_url:
                    unique_linkedin_urls.add(linkedin_url.strip())  # Remove any leading/trailing whitespace
            
            unique_count = len(unique_linkedin_urls)
            logger.info(f"Found {unique_count} unique LinkedIn URLs")
            return unique_count
        else:
            logger.warning("No LinkedIn URLs found in the database")
            return 0  # Return 0 instead of "Error" for consistency
    
    except Exception as e:
        logger.error(f"Error counting unique LinkedIn URLs: {str(e)}", exc_info=True)
        return None  # Return None to indicate an error occurred


# ------------------------------


def count_current_profiles_with_urls(supabase_client):
    """
    Counts the number of unique LinkedIn URLs in the Unicorn-Stealth-Founder-Profiles table.
    
    Args:
        supabase_client: An initialized and authenticated Supabase client.
        
    Returns:
        The number of unique LinkedIn URLs as an integer.
        Returns None if an error occurs during the query.
    """
    try:
        logger.info("Attempting to count unique LinkedIn URLs in Unicorn-Stealth-Founder-Profiles table")
        
        # Step 1: Query for distinct LinkedIn URLs, excluding NULL and empty strings
        response = supabase_client.table("Current-Employee-Profiles")\
            .select("linkedin_url")\
            .neq("linkedin_url", None)\
            .neq("linkedin_url", "")\
            .neq("profile_status", "")\
            .execute()
        
        # Step 2: Check if data is returned
        if response.data:
            # Extract 'linkedin_url' from each record and add to a set for uniqueness
            unique_linkedin_urls = set()
            for record in response.data:
                linkedin_url = record.get("linkedin_url")
                if linkedin_url:
                    unique_linkedin_urls.add(linkedin_url.strip())  # Remove any leading/trailing whitespace
            
            unique_count = len(unique_linkedin_urls)
            logger.info(f"Found {unique_count} unique LinkedIn URLs in Current Employees")
            return unique_count
        else:
            logger.warning("No LinkedIn URLs found in the database")
            return 0  # Return 0 instead of "Error" for consistency
    
    except Exception as e:
        logger.error(f"Error counting unique LinkedIn URLs: {str(e)}", exc_info=True)
        return None  # Return None to indicate an error occurred


# ------------------------------


def query_current_employees_table(supabase, current_company, filter_repeat_founder=False, filter_senior_operator=False):
    """
    Query the Supabase "Current-Employees-Profiles" table table with filtering options.
    
    Args:
        supabase: Supabase client
        current_company: Company name to search for
        filter_repeat_founder: Boolean to filter for repeat founders
        filter_senior_operator: Boolean to filter for senior operators
    """
    try:
        # Start with base query
        query = supabase.table("Current-Employee-Profiles")\
            .select("*")\
            .eq("current_company", current_company)

        # Add conditional filters
        if filter_repeat_founder:
            query = query.eq("is_repeat_founder", True)
        
        if filter_senior_operator:
            query = query.eq("is_senior_operator", True)

        # Execute query
        response = query.execute()
        
        # Process response
        if response.data and len(response.data) > 0:
            logger.info(f"Successfully retrieved profiles for {current_company}")
            logger.info(f"Additional filters - Repeat Founder: {filter_repeat_founder}, Senior Operator: {filter_senior_operator}")
            logger.info(f"Found {len(response.data)} matching profiles")
            return response.data
        else:
            # Build filter message for logging
            filter_msg = []
            if filter_repeat_founder:
                filter_msg.append("Repeat Founders")
            if filter_senior_operator:
                filter_msg.append("Senior Operators")
            
            filter_str = f" with filters ({', '.join(filter_msg)})" if filter_msg else ""
            logger.warning(f"No profiles found for {current_company}{filter_str}")
            return []

    except Exception as e:
        logger.error(f"Error querying profiles for {current_company}: {str(e)}")
        return []


# ------------------------------


def get_current_employees_db(supabase_client) -> List[str]:
    """
    Fetch unique company names from the 'current_company' column of the 
    'Current-Employee-Profiles' table for dropdown selection.
    
    Args:
        supabase_client: An initialized and authenticated Supabase client.
        
    Returns:
        A list of unique company names present in the 'current_company' column.
        Returns an empty list if no companies are found or an error occurs.
    """
    try:
        logger.info("Attempting to fetch unique current_company names from profiles table")
        
        # Step 1: Fetch all non-null and non-empty current_company entries
        response = supabase_client.table("Current-Employee-Profiles")\
            .select("current_company")\
            .neq("current_company", None)\
            .neq("current_company", "")\
            .execute()
        print(response)
        if not response.data:
            logger.warning("No current_company entries found in Current-Employee-Profiles table")
            return []
        
        # Step 2: Extract company names and normalize them
        current_companies = [record["current_company"].strip() for record in response.data if record.get("current_company")]
        logger.info(f"Retrieved {len(current_companies)} current_company entries from profiles table")
        
        # Step 3: Deduplicate the company names
        unique_current_companies = sorted(list(set(current_companies)))
        logger.info(f"Unique current_company entries count: {len(unique_current_companies)}")
        
        return unique_current_companies
    
    except Exception as e:
        logger.error(f"Error fetching companies: {str(e)}", exc_info=True)
        return []