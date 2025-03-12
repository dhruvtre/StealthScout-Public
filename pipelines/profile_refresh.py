# All necessary imports

import os
from profile_status_classifier import *
import aiohttp
from typing import Dict
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import sys
from typing import List
import asyncio
sys.path.append('.')
from profile_status_classifier import check_profile_status_with_verification
from insert_profile import create_supabase_client
import logging

# Basic logging configuration 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('stealthscout')

# Load environment variables from the correct path

load_dotenv()
OPENAI_API_KEY = os.getenv("openai_api_key")
client = OpenAI(api_key=OPENAI_API_KEY)

# Defining All Relevant Functions
# 1. Fetch New Profile Data - fetch_fresh_profile_data
# 2. Get Current Profile from DB - get_current_profile
# 3. Compare Profile Changes - compare_profile_changes
# 4. Prepare Profile Updates - prepare_profile_updates
# 5. Update Profile in DB - update_profile_in_db
# 6. Run the End-to-End Refresh Pipeline - refresh_single_profile
# 7. Filter Functions - get_company_profiles, get_status_profiles
# 8. main Execution Function - main()
# ------------------------------


async def fetch_fresh_profile_data(api_key: str, linkedin_url: str) -> Dict:
    """
    Fetches fresh profile data from LinkedIn API for profile refresh.
    
    Args:
        api_key: RapidAPI key
        linkedin_url: LinkedIn profile URL to refresh
        
    Returns:
        Dict: Contains either:
            - Fresh profile data with relevant fields
            - Error information with status and message
    """
    url = "https://fresh-linkedin-profile-data.p.rapidapi.com/get-linkedin-profile"
    querystring = {
        "linkedin_url": linkedin_url,
        "include_skills": "false",
        "include_certifications": "false",
        "include_publications": "false",
        "include_honors": "false",
        "include_volunteers": "false",
        "include_projects": "false",
        "include_patents": "false",
        "include_courses": "false",
        "include_organizations": "false",
        "include_company_public_url": "false"
    }
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "fresh-linkedin-profile-data.p.rapidapi.com"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=querystring) as response:
                if response.status == 200:
                    response_data = await response.json()
                    profile_data = response_data.get('data', {})

                    profile = {
                    "first_name": profile_data.get('first_name', ''),
                    "last_name": profile_data.get('last_name', ''),
                    "full_name": profile_data.get('full_name', ''),
                    "headline": profile_data.get('headline', ''),
                    "linkedin_url": profile_data.get('linkedin_url', ''),
                    "job_title": profile_data.get('job_title', ''),
                    "follower_count": profile_data.get('follower_count', ''),
                    "connection_count": profile_data.get('connection_count', ''),
                    "city": profile_data.get('city', ''),
                    "location": profile_data.get('location', ''),


                    # Experience details
                    "experience": [{
                        "company": exp.get('company', ''),
                        "company_linkedin_url": exp.get('company_linkedin_url', ''),
                        "date_range": exp.get('date_range', ''),
                        "duration": exp.get('duration', ''),
                        "title": exp.get('title', '')
                        } for exp in profile_data.get('experiences', [])],

                    # Education details
                    "education": [{
                        "school": edu.get('school', ''),
                        "degree": edu.get('degree', ''),
                        "field_of_study": edu.get('field_of_study', ''),
                        "date_range": edu.get('date_range', '')
                        } for edu in profile_data.get('educations', [])]
                    }
                    logger.info(f"Successfully scraped LinkedIn profile: {linkedin_url}")
                    return profile

                elif response.status == 429:  # Rate limit exceeded
                    logger.info(f"Rate limit reached while fetching profile: {linkedin_url}")
                    return {
                        "error": "rate_limit_exceeded",
                        "message": "API rate limit reached",
                        "status_code": response.status
                    }
                    
                else:
                    logger.info(f"Failed to fetch profile {linkedin_url}. Status code: {response.status}")
                    return {
                        "error": "api_error",
                        "message": f"Request failed with status code {response.status}",
                        "status_code": response.status
                    }

    except aiohttp.ClientError as e:
        logger.info(f"Network error while fetching profile {linkedin_url}: {str(e)}")
        return {
            "error": "network_error",
            "message": str(e)
        }
    
    except Exception as e:
        logger.info(f"Unexpected error while fetching profile {linkedin_url}: {str(e)}")
        return {
            "error": "unexpected_error",
            "message": str(e)
        }


# ------------------------------


async def get_current_profile(supabase_client, linkedin_url: str, table_name: str, search_company:str) -> Dict:
    """
    Retrieves current profile data from Supabase database.
    
    Args:
        supabase_client: Initialized Supabase client
        linkedin_url: LinkedIn URL of the profile to retrieve
        table_name = Name of the table to search for the profile
        search_company = Company currently employed in or ex-employee in
    
    Returns:
        Dict: Current profile data if found, error dict if not found/error occurs
    """
    try:
        logger.info("Setting the company_param parameter based on the table_name")
        if table_name == "Current-Employee-Profiles":
            company_param = "current_company"
        elif table_name == "Unicorn-Stealth-Founder-Profiles":
            company_param = "search_company"
        logger.info(f"Retrieving current profile data for: {linkedin_url} from {table_name}")
        
        response = supabase_client.table(table_name)\
            .select("*")\
            .eq("linkedin_url", linkedin_url)\
            .eq(company_param, search_company)\
            .execute()
        
        if response.data and len(response.data) > 0:
            logger.info(f"Successfully retrieved profile data for {linkedin_url} with {search_company}")
            return response.data[0]
        
        logger.info(f"No profile found for {linkedin_url} in {search_company}")
        return {"error": "Profile not found in database"}

    except Exception as e:
        logger.info(f"Error retrieving profile {linkedin_url}: {str(e)}")
        return {"error": f"Database error: {str(e)}"}


# ------------------------------


def compare_profile_changes(old_profile: dict, new_profile: dict) -> dict:
    """
    Compares old and new profile data to detect all field changes.
    
    Args:
        old_profile: Current profile data from database
        new_profile: Fresh profile data from LinkedIn
        
    Returns:
        dict: Contains changes detected across all fields
    """
    changes = {
        "changed_fields": [],
        "changes": {},
        "has_changes": False
    }
    
    # Basic field comparison
    simple_fields = [
        "first_name", "last_name", "headline", "job_title",
        "location", "follower_count", "connection_count"
    ]
    
    for field in simple_fields:
        old_value = old_profile.get(field, "")
        new_value = new_profile.get(field, "")
        if old_value != new_value:
            changes["changed_fields"].append(field)
            changes["changes"][field] = {
                "old": old_value,
                "new": new_value
            }
            changes["has_changes"] = True
    
    # Experience comparison - all roles
    old_exp = old_profile.get("experience", [])
    new_exp = new_profile.get("experience", [])
    
    if len(old_exp) != len(new_exp):
        changes["changed_fields"].append("experience_count")
        changes["changes"]["experience_count"] = {
            "old": len(old_exp),
            "new": len(new_exp)
        }
        changes["has_changes"] = True
    
    # Check first role in detail (most recent)
    if old_exp and new_exp:
        exp_fields = ["company", "title", "duration", "date_range"]
        for field in exp_fields:
            old_value = old_exp[0].get(field, "")
            new_value = new_exp[0].get(field, "")
            if old_value != new_value:
                changes["changed_fields"].append(f"recent_experience_{field}")
                changes["changes"][f"recent_experience_{field}"] = {
                    "old": old_value,
                    "new": new_value
                }
                changes["has_changes"] = True
    
    # Education comparison
    old_edu = old_profile.get("education", [])
    new_edu = new_profile.get("education", [])
    if len(old_edu) != len(new_edu):
        changes["changed_fields"].append("education_count")
        changes["changes"]["education_count"] = {
            "old": len(old_edu),
            "new": len(new_edu)
        }
        changes["has_changes"] = True
    
    # Previous companies comparison
    old_companies = set(old_profile.get("previous_companies", []))
    new_companies = set(exp.get("company", "") for exp in new_exp if exp.get("company"))
    if old_companies != new_companies:
        changes["changed_fields"].append("previous_companies")
        changes["changes"]["previous_companies"] = {
            "old": list(old_companies),
            "new": list(new_companies)
        }
        changes["has_changes"] = True
    
    # Detailed logging
    logger.info(f"Profile comparison completed. Found changes: {changes['has_changes']}")
    if changes["has_changes"]:
        logger.info(f"Changed fields: {changes['changed_fields']}")
        for field in changes["changed_fields"]:
            old = changes["changes"][field]["old"]
            new = changes["changes"][field]["new"]
            logger.info(f"  {field}: {old} -> {new}")
    
    return changes


# ------------------------------


async def prepare_profile_updates(old_profile: dict, new_profile: dict, detected_changes: dict) -> dict:
    """
    Prepares profile updates using complete new profile data while tracking changes.
    
    Args:
        old_profile: Current profile data from database
        new_profile: Fresh profile data from LinkedIn
        detected_changes: Changes detected for logging purposes
    
    Returns:
        dict: Complete profile update data
    """
    updates = {
        "fields_to_update": {
            # Basic profile fields
            "first_name": new_profile.get("first_name", ""),
            "last_name": new_profile.get("last_name", ""),
            "headline": new_profile.get("headline", ""),
            "job_title": new_profile.get("job_title", ""),
            "location": new_profile.get("location", ""),
            "follower_count": new_profile.get("follower_count", ""),
            "connection_count": new_profile.get("connection_count", ""),
            
            # Detailed fields
            "experience": new_profile.get("experience", []),
            "education": new_profile.get("education", []),
            "previous_companies": [
                exp.get("company", "") 
                for exp in new_profile.get("experience", [])
                if exp.get("company")
            ]
        },
        "refresh_metadata": {
            "last_attempted_refresh_timestamp": datetime.utcnow().isoformat(),
            "refresh_status": "success"
        }
    }

    # Define non-critical fields that can change without manual verification
    non_critical_fields = ['follower_count', 'connection_count', 'recent_experience_duration']

    # Log any detected changes for monitoring
    if detected_changes["has_changes"]:
        logger.info(f"Profile changes detected for {new_profile.get('linkedin_url', '')}:")
        for field in detected_changes["changed_fields"]:
            old_value = detected_changes["changes"][field]["old"]
            new_value = detected_changes["changes"][field]["new"]
            logger.info(f"  {field}: {old_value} -> {new_value}")
    
    # Check if ONLY non-critical fields have changed
    changed_fields = set(detected_changes["changed_fields"])
    critical_changes = changed_fields - set(non_critical_fields)
    
    # Determine if we can auto-approve
    auto_approve = len(critical_changes) == 0 and len(changed_fields) > 0

    if auto_approve:
        logger.info(f"Auto-approving status update (only non-critical fields changed: {list(changed_fields)})")
    else:
        if len(changed_fields) == 0:
            logger.info("Manual verification required (no changes detected)")
        else:
            logger.info(f"Manual verification required (critical fields changed: {list(critical_changes)})")

    # Get new status classification with auto_approve flag
    classification = await check_profile_status_with_verification(client, new_profile, auto_approve=auto_approve, old_status=old_profile.get("profile_status"))

    if classification["status"] != old_profile.get("profile_status"):
        #handle_status_change(new_profile, old_profile.get("profile_status"), classification["status"])
        updates["fields_to_update"]["profile_status"] = classification["status"]
        updates["fields_to_update"]["status_confidence_label"] = classification["confidence_label"]
        detected_changes["changed_fields"].append("profile_status")
        detected_changes["changes"]["profile_status"] = {
            "old": old_profile.get("profile_status"),
            "new": classification["status"],
            "confidence": classification["confidence_label"]
        }

    # Log status changes specifically
    if classification["status"] != old_profile.get("profile_status"):
        logger.info(
            f"Profile status updated from '{old_profile.get('profile_status')}' to "
            f"'{classification['status']}' with confidence '{classification['confidence_label']}'"
        )

    return updates


# ------------------------------


def update_profile_in_db(supabase_client, linkedin_url: str, updates: dict, search_company: str, table_name: str) -> bool:
   """
   Updates profile data and refresh metadata in database.
   
   Args:
       supabase_client: Initialized Supabase client
       linkedin_url: Profile to update
       updates: Dictionary containing:
           - fields_to_update: Profile fields that need updating
           - refresh_metadata: Refresh timestamps and status
        table_name: Name of the table to update
   Returns:
       bool: True if update successful, False otherwise
   """
   try:
       logger.info(f"Getting company_param based on {table_name}")
       if table_name == "Current-Employee-Profiles":
        company_param = "current_company"
       elif table_name == "Unicorn-Stealth-Founder-Profiles":
        company_param = "search_company"
       elif table_name not in ["Current-Employee-Profiles", "Unicorn-Stealth-Founder-Profiles"]:
        raise ValueError(f"Invalid table name: {table_name}")
       logger.info(f"Updating profile {linkedin_url} in database {table_name}")
       
       # Combine profile updates and refresh metadata into single update
       update_data = {
           **updates.get("fields_to_update", {}),
           **updates.get("refresh_metadata", {})
       }
       logger.info(f"Updating fields: {list(update_data.keys())}")
       # Update the profile in database
       response = supabase_client.table(table_name)\
           .update(update_data)\
           .eq("linkedin_url", linkedin_url)\
           .eq(company_param, search_company)\
           .execute()
           
       if response.data:
           logger.info(f"Successfully updated profile: {linkedin_url} in database {table_name}")
           logger.info(f"Updated fields: {list(update_data.keys())}")
           return True
           
       else:
           logger.info(f"Failed to update profile: {linkedin_url}")
           return False
           
   except Exception as e:
       logger.info(f"Error updating profile {linkedin_url}: {str(e)}")
       return False


# ------------------------------


async def refresh_single_profile(supabase_client, api_key: str, linkedin_url: str, search_company: str, table_name: str) -> dict:
    """
    Main orchestrator function for refreshing a single profile.
    
    Args:
        supabase_client: Initialized Supabase client
        api_key: RapidAPI key
        linkedin_url: LinkedIn URL to refresh
        
    Returns:
        dict: Results of refresh operation including:
            - success: bool indicating if refresh completed
            - changes: any changes detected and applied
            - status: final status of refresh
    """
    try:
        # Step 1: Get current profile
        current_profile = await get_current_profile(supabase_client, linkedin_url, table_name, search_company)
        if "error" in current_profile:
            return {"success": False, "error": current_profile["error"]}
            
        # Step 2: Fetch fresh profile data
        fresh_profile = await fetch_fresh_profile_data(api_key, linkedin_url)
        if "error" in fresh_profile:
            return {"success": False, "error": fresh_profile["error"]}
            
        # Step 3: Compare profiles and detect changes
        detected_changes = compare_profile_changes(current_profile, fresh_profile)
        
        # Step 4: Prepare updates
        if detected_changes["has_changes"]:
            updates = await prepare_profile_updates(current_profile, fresh_profile, detected_changes)
        
            # Step 5: Update database
            update_success = update_profile_in_db(supabase_client, linkedin_url, updates, search_company, table_name)
            old_exp = current_profile.get('experience', [])
            new_exp = fresh_profile.get('experience', [])
            
            return {
                "success": update_success,
                "changes": detected_changes if detected_changes["has_changes"] else "",
                "status": "updated" if update_success else "failed",
                "profile_id": current_profile.get("id"),
                "old_exp": old_exp,
                "new_exp": new_exp,
                "full_name": fresh_profile.get("full_name"),
            }
        else:
            refresh_metadata = {
                "refresh_metadata": {
                    "last_attempted_refresh_timestamp": datetime.utcnow().isoformat(),
                    "refresh_status": "success"
                }
            }
            update_success = update_profile_in_db(supabase_client, linkedin_url, refresh_metadata, search_company, table_name)
            return {
                "success": True,
                "changes": {  # Make changes a dictionary
            "last_attempted_refresh_timestamp": refresh_metadata["refresh_metadata"]["last_attempted_refresh_timestamp"],
            "refresh_status": refresh_metadata["refresh_metadata"]["refresh_status"]
            },
                "status": "no_changes",
                "profile_id": current_profile.get("id")
            }
        
    except Exception as e:
        logger.info(f"Error in refresh pipeline for {linkedin_url}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "status": "failed"
        }


# ------------------------------


async def get_status_profiles(supabase_client, table_name, status: str) -> List[str]:
    """
    Fetches all LinkedIn URLs for profiles with a specific status.
    
    Args:
        supabase_client: Initialized Supabase client
        status: Profile status to fetch profiles for
    
    Returns:
        List[str]: List of LinkedIn URLs for the profiles
    """
    try:
        logger.info(f"Fetching profiles with status: {status}")
        response = supabase_client.table(table_name)\
            .select("linkedin_url")\
            .eq("profile_status", status)\
            .execute()
            
        if response.data:
            urls = [profile['linkedin_url'] for profile in response.data]
            logger.info(f"Found {len(urls)} profiles with status: {status}")
            return urls
            
        logger.info(f"No profiles found with status: {status}")
        return []
        
    except Exception as e:
        logger.info(f"Error fetching profiles with status {status}: {str(e)}")
        return []


# ------------------------------


async def get_company_profiles(supabase_client, search_company: str, table_name: str) -> List[str]:
    """
    Fetches all LinkedIn URLs for profiles associated with a specific company.
    Args:
        supabase_client: Initialized Supabase client
        search_company: Company name to fetch profiles for
    Returns:
        List[str]: List of LinkedIn URLs for the company's profiles
    """
    try:
        logger.info(f"Fetching company_param based on {table_name}")
        if table_name == "Current-Employee-Profiles": 
            company_param = "current_company"
            status_list = ["current_employee"]
        elif table_name == "Unicorn-Stealth-Founder-Profiles":
            company_param = "search_company"
            status_list = ["stealth", "recently_quit", "building_in_public"]
        elif table_name not in ["Current-Employee-Profiles", "Unicorn-Stealth-Founder-Profiles"]:
            raise ValueError(f"Invalid table name: {table_name}")
        
        logger.info(f"Fetching profiles for company: {search_company}")
        response = supabase_client.table(table_name)\
            .select("linkedin_url")\
            .eq(company_param, search_company)\
            .execute()
            
        if response.data:
            urls = [profile['linkedin_url'] for profile in response.data]
            logger.info(f"Found {len(urls)} profiles for {search_company}")
            return urls
            
        logger.info(f"No profiles found for company: {search_company}")
        return []
        
    except Exception as e:
        logger.info(f"Error fetching profiles for {search_company}: {str(e)}")
        return []


# ------------------------------


async def main():
    rapidapi_api_key = os.getenv("rapidapi_api_key")
    # Environment variables
    supabase_url = os.getenv("supabase_url")
    supabase_key = os.getenv("supabase_key") 
    supabase_client = create_supabase_client(supabase_url, supabase_key)
    print("Select table:\n1. Current-Employee-Profiles\n2. Unicorn-Stealth-Founder-Profiles")
    choice = input("Enter 1 or 2: ").strip()
    table_name = "Current-Employee-Profiles" if choice == "1" else "Unicorn-Stealth-Founder-Profiles"
    # Initialize clients2
    company_to_update = input("Enter company name in DB to update:")
    test_list_of_companies = [company_to_update]
    try:
        for company in test_list_of_companies:
            logger.info(f"Starting refresh for company: {company}")
            try:
                # Get profiles for company
                profiles = await get_company_profiles(supabase_client, company, table_name)
                logger.info(f"Found {len(profiles)} profiles for {company}")
       
                stats = {"processed": 0, "updated": 0, "failed": 0, "status_changes": []}
       
                # Process each profile
                for profile in profiles:
                    try:
                        result = await refresh_single_profile(supabase_client, rapidapi_api_key, profile, search_company=company, table_name=table_name)
                        stats["processed"] += 1
               
                        if result["success"]:
                            stats["updated"] += 1
                        
                        changes = result.get("changes", {})
                        logger.info("Checking for profile status changes")
                        if "profile_status" in changes.get("changed_fields", []):
                            logger.info("Profile status changes detected")
                            try:
                                status_change = changes['changes']['profile_status']
                                experience_changes = {}
                                logger.info("Collecting experience changes")
                                # Collect experience changes if any
                                for field in ['recent_experience_company', 'recent_experience_title', 'recent_experience_duration', 'recent_experience_date_range']:
                                    if field in changes['changes']:
                                        experience_changes[field.replace('recent_experience_', '')] = changes['changes'][field]
                                logger.info(f"Experience changes collected.")
                                logger.info("Preparing status update.") 
                                prev_role = result['old_exp'][0] if result['old_exp'] else None
                                curr_role = result['new_exp'][0] if result['new_exp'] else None
                                status_update = {
                                'profile_id': result['profile_id'],  # Get id from the profile in result
                                'linkedin_url': profile,
                                'old_status': status_change['old'],
                                'new_status': status_change['new'],
                                'status_confidence': status_change.get('confidence', 'HIGH'),
                                'experience_changes': experience_changes if experience_changes else None,
                                'prev_role': prev_role,
                                'curr_role': curr_role
                                }
                                logger.info(f"Attempting to insert status update: {status_update}")
                                # Insert into status updates table using id from existing profile
                                update_response = supabase_client.table('stealth_founder_status_update_table')\
                                .insert(status_update)\
                                .execute()
                            
                                if update_response.data:
                                    print(update_response.data)
                                    logger.info("Successfully inserted status update")
                                    stats["status_changes"].append({
                                    "url": profile,
                                "old": result["changes"]["changes"]["profile_status"]["old"],
                                        "new": result["changes"]["changes"]["profile_status"]["new"]
                                    })
                                else:
                                    logger.info("Failed to insert status update")                          
                            except Exception as e:
                                logger.info(f"Error inserting status update: {str(e)}")
                        else:
                            logger.info("No profile status changes detected")
                        await asyncio.sleep(3)  # Basic rate limiting
               
                    except Exception as e:
                        stats["failed"] += 1
                        logger.info(f"Failed processing {profile}: {str(e)}")
                logger.info(f"Company refresh complete. Stats: {stats}")
            except Exception as e:
                logger.info(f"Failed processing company {company}: {str(e)}")
            await asyncio.sleep(9)  # Basic rate limiting
    except Exception as e:
        logger.info(f"Failed processing list of companies {test_list_of_companies}: {str(e)}")


# ------------------------------

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())