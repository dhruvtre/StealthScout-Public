# All necessary imports

import sys
import asyncio
import aiohttp
from supabase import create_client, Client
import json
from typing import Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging

# Basic logging configuration 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('stealthscout')

# Environment variables

load_dotenv()
supabase_url = os.getenv("supabase_url")
supabase_key = os.getenv("supabase_key")
rapidapi_api_key = os.getenv("rapidapi_api_key")
openai_api_key = os.getenv("openai_api_key")

# Importing AI labelling functions and examples

with open('senior_operator_labelling_examples.json', 'r') as f:
    labeled_examples = json.load(f)
from senior_operator_labeller import senior_operator_labelling_call
from profile_status_classifier import check_profile_status_with_verification



# Defining All Relevant Functions
# 1. Check Existing Profile - check_existing_profile
# 2. Scrape LinkedIn Profile - linkedin_profile_scraper
# 3. Create Supabase Client - create_supabase_client
# 4. Insert Profile to Supabase - insert_profiles_to_db
# 5. Labelling Specific Functions - check_repeat_founder, extract_company_role, check_senior_operator
# 6. Format linkedin_urls Consistently  - ensure_trailing_slash
# 7. Insert Labels to Database - update_profile_labels, prepare_profile_labels
# 8. Run the End-to-End Insert Pipeline - process_linkedin_profile
# 9. main Execution Function - main()
# ------------------------------


def check_existing_profile(supabase_client, linkedin_url: str, target_company: str, table_name: str) -> Optional[Dict]:
    """
    Check if a LinkedIn profile already exists in the database for the given company.
    
    Args:
        supabase_client: Initialized Supabase client
        linkedin_url: The LinkedIn URL to check
        target_company: Company to check against (current_company in case of Current_employees and search_company in case of Unicorn-Stealth-Founder-Profiles)
        table_name: To determine which table to search based on if stealth or current employee.
    
    Returns:
        Dict containing profile data if found, None otherwise
    """
    try:
        logger.info("Check for relevant table to search and setting company parameter.")
        if table_name == "Current-Employee-Profiles": 
            company_param = "current_company"
        elif table_name == "Unicorn-Stealth-Founder-Profiles":
            company_param = "search_company"
        logger.info(f"Searching table: {table_name} with company parameter: {company_param}")
        

        logger.info(f"Checking if profile {linkedin_url} exists.")
        
        # Query the database for the profile
        response = supabase_client.table(table_name)\
            .select("*")\
            .eq("linkedin_url", linkedin_url)\
            .eq(company_param, target_company)\
            .execute()
        
        # Check if we got any results
        if response.data and len(response.data) > 0:
            logger.info(f"Found existing profile for {linkedin_url}.")
            return True
        
        logger.info(f"No existing profile found for {linkedin_url}.")
        return False

    except Exception as e:
        error_msg = f"Error checking profile existence: {str(e)}"
        logger.error(error_msg)
        return {
            "exists": None,
            "profile_data": None,
            "message": error_msg,
            "error": str(e)
        }


# ------------------------------


async def linkedin_profile_scraper(api_key, linkedin_url):
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
    logger.info(f"Scraping LinkedIn profile: {linkedin_url}")
    # Using aiohttp for asynchronous request
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=querystring) as response:
            if response.status == 200:
                response_data = await response.json()
                profile_data = response_data.get('data', {})

                # Profile fields with safe defaults if missing
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
            
                # Previous_companies array
                "previous_companies": [
                    exp.get('company', '') 
                    for exp in profile_data.get('experiences', [])
                        if exp.get('company')
                    ],

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

            else:
                logger.error(f"Failed to scrape LinkedIn profile: {linkedin_url}. Status code: {response.status}")
                return {'error': f"Request failed with status code {response.status}"}


# ------------------------------


def create_supabase_client(supabase_url, supabase_key):
    supabase: Client = create_client(supabase_url, supabase_key)
    return supabase


# ------------------------------


# Inserting profiles into Supabase
def insert_profiles_to_db(profile, supabase, target_company, table_name):
    logger.info("Setting company parameters.")
    if table_name == "Current-Employee-Profiles": 
        company_param = "current_company"
    elif table_name == "Unicorn-Stealth-Founder-Profiles":
        company_param = "search_company"
    elif table_name not in ["Current-Employee-Profiles", "Unicorn-Stealth-Founder-Profiles"]:
        raise ValueError(f"Invalid table name: {table_name}")
    logger.info(f"Inserting profile into table: {table_name} with company parameter: {company_param}")
    logger.info("________Getting data from profile.")
    data = {
            "linkedin_url": profile.get("linkedin_url"),
            "first_name": profile.get("first_name"),
            "last_name": profile.get("last_name"),
            "full_name": profile.get("full_name"),
            "headline": profile.get("headline"),
            "job_title": profile.get("job_title"),
            "follower_count": profile.get("follower_count"),
            "connection_count": profile.get("connection_count"),
            "location": profile.get("location"),
            "experience": profile.get("experience"),
            "education": profile.get("education"),
            "previous_companies": profile.get("previous_companies"),
            company_param: target_company
        }
        
    try:
            # Insert the profile data into the 'Unicorn-Stealth-Founder-Profiles' table
            logger.info("________Trying profile insert")
            response = supabase.table(table_name).insert(data).execute()

            if response.get("status_code") or response.get("error"):
                logger.error(f"Failed to insert profile {profile['linkedin_url']}: {response.get('error')}")
            else:
                logger.info(f"Successfully inserted profile: {profile['linkedin_url']}")

    except Exception as e:
            logger.error(f"Exception occurred while inserting profile {profile['linkedin_url']}: {str(e)}")


# ------------------------------


def check_repeat_founder(profile: Dict) -> bool:
    """
    Checks if the profile contains multiple roles with founder-related keywords.
    If there are ambiguous entries, the profile is flagged for manual review.

    Parameters:
    - profile: dict, The profile containing experience data.

    Returns:
    - dict: with 'is_repeat_founder' as True/False.
    """
    # Define the keywords to automatically label as founder
    founder_keywords = ['founder', 'co-founder', 'co founder', 'chief executive officer', 'ceo']
    founder_roles = []
    try:
        profile_name = profile.get('full_name', 'Unknown')
        if not profile.get('experience'):
            logger.warning(f"No experience found for profile {profile_name}")
            return False
    
        # Step 1: Iterate over the experience list
        for experience in profile.get('experience', []):
            role = experience.get('title', '').lower()
            if any(keyword in role for keyword in founder_keywords):
                logger.info(f"Found founder role: {role} at {experience.get('company', 'Unknown')}")
                founder_roles.append(experience)

        # Step 2: Determine if the profile should be flagged for review
        if len(founder_roles) > 1:
            logger.info(f"Profile {profile_name} identified as repeat founder with {len(founder_roles)} founder roles")
            is_repeat_founder = True
            return is_repeat_founder
        else:
            logger.info(f"Profile {profile_name} is not a repeat founder")
            is_repeat_founder = False
            return is_repeat_founder
    except Exception as e:
        logger.error(f"Error checking repeat founder status for {profile_name}: {str(e)}")
        is_repeat_founder = False
        return is_repeat_founder


# ------------------------------


def extract_company_role(profile: Dict, search_company: str) -> str:
    """
    Extracts role at specified company from profile experience.
    Returns formatted role string or empty string if not found.
    """
    try:
        if not profile.get('experience'):
            logger.warning(f"No experience found for profile {profile.get('full_name', 'Unknown')}")
            return ''
    
        # Display the profile name and search company
        print(f"\nProfile: {profile.get('full_name', 'Unknown Name')}")
        print(f"Search Company: {search_company}")
        print("Experience List:")

        # Display all the experiences of the profile
        experiences = profile.get('experience', [])
        for idx, experience in enumerate(experiences):
            company = experience.get('company', 'Unknown Company')
            title = experience.get('title', 'Unknown Role')
            duration = experience.get('duration', 'Unknown Duration')
            date_range = experience.get('date_range', 'Unknown Date Range')

        # Extract role(s) at the search company
        relevant_experiences = [
                exp for exp in experiences if exp.get('company', '').lower() == search_company.lower()
            ]

        role_at_company = ''

        # Handle cases based on the number of relevant experiences
        if len(relevant_experiences) == 1:
            # Single matching experience, auto-suggest
            role = relevant_experiences[0].get('title', 'Unknown Role')
            duration = relevant_experiences[0].get('duration', 'Unknown Duration')
            role_at_company = f"{role} at {search_company} for {duration}"

        elif len(relevant_experiences) > 1:
            logger.info(f"Multiple roles found at {search_company}. Please enter the role at company statement.")
            for idx, exp in enumerate(relevant_experiences):
                print(f"{idx + 1}. {exp.get('title')} ({exp.get('duration')})")
            role_at_company = input("Please enter the role at company statement")

        # If no matching experience is found for the search_company
        else: 
            logger.warning(f"No relevant experience found for {profile['full_name']} at {search_company}.")
            role_at_company = input("Please enter the role at company statement")
    
        logger.info(f"Final role extracted: {role_at_company}")
        return role_at_company
    except Exception as e:
        logger.error(f"Error extracting company role for {profile.get('full_name', 'Unknown')}: {str(e)}")
        role_at_company = ''
        return role_at_company


# ------------------------------


def check_senior_operator(profile: Dict, client, max_examples=10) -> bool:
    """
    Determines if a profile is a senior operator using AI labelling.
    Falls back to manual input only if AI call fails completely.
    """
    if not profile.get('experience'):
        logger.warning(f"No experience found for profile {profile.get('full_name', 'Unknown')}")
        return False

    logger.info(f"\nProfile: {profile.get('full_name', 'Unknown Name')}")
    
    # Make AI call to get label
    logger.info("Making AI call for labelling.")
    try:
        ai_response = senior_operator_labelling_call(client, profile, labeled_examples, max_examples=max_examples)
        logger.info("AI call for labelling complete.")
        
        if ai_response is not None:  # Changed to check for None instead of truthiness
            is_senior_operator = False
            if ai_response.lower() == 'true':
                is_senior_operator = True
                logger.info(f"Senior operator classification: {is_senior_operator}")
                return is_senior_operator
            elif ai_response.lower() == 'false':
                is_senior_operator = False
                return is_senior_operator
            else:
                logger.info(f"AI response neither 'true' nor 'false'.\n Output: {ai_response.lower()}")
                logger.info("Returning the default value of 'false")
                is_senior_operator = False
                return is_senior_operator
        else:
            logger.warning("No AI response received")
            manual_label = input("Please manually input (true/false): ").strip().lower()
            return manual_label

    except Exception as e:
        logger.error(f"Error determining senior operator status: {str(e)}")
        manual_label = input("Please manually input (true/false): ").strip().lower()
        return manual_label == 'true'


# ------------------------------


def prepare_profile_w_labels(profile_status: str, is_repeat_founder: bool, role_search_company: str, linkedin_url: str, is_senior_operator: bool, table_name: str) -> Dict:
   """
   Prepares dictionary with profile labels and identifiers for database update.
   """
   logger.info(f"Preparing company_param for label update.")
   if table_name == "Current-Employee-Profiles":
       company_param = "role_at_current_company"
   elif table_name == "Unicorn-Stealth-Founder-Profiles":
       company_param = "role_at_company_searched"
    
   profile_data_labels = {
       "profile_status": profile_status["status"],
       "status_confidence_label": profile_status["confidence_label"],
       "linkedin_url": linkedin_url,
       "is_repeat_founder": is_repeat_founder, 
       company_param: role_search_company,
       "is_senior_operator": is_senior_operator
   }
   return profile_data_labels


# ------------------------------


def update_profile_labels(profile_data: Dict, supabase_client, linkedin_url: str, table_name: str) -> None:
   """
   Updates profile labels in database.
   """
   try:
       logger.info("Setting company parameter for label update.")
       if table_name == "Current-Employee-Profiles":
              company_param = "role_at_current_company"
       if table_name == "Unicorn-Stealth-Founder-Profiles":
              company_param = "role_at_company_searched"
       logger.info(f"Updating labels for profile: {linkedin_url}")
       response = supabase_client.table(table_name)\
           .update({
               'is_repeat_founder': profile_data.get('is_repeat_founder', False),
               company_param: profile_data.get(company_param, ''),
               'is_senior_operator': profile_data.get('is_senior_operator', False), 
               'profile_status': profile_data.get('profile_status'),
               'status_confidence_label': profile_data.get('status_confidence_label')
           })\
           .eq('linkedin_url', linkedin_url)\
           .execute()
       
       logger.info(f"Update response: {response}")
       
   except Exception as e:
       logger.error(f"Error updating profile labels: {str(e)}")


# ------------------------------


import asyncio
from typing import Dict, Optional

async def process_linkedin_profile(linkedin_url: str, target_company: str, table_name: str):
   """Main pipeline to process a single LinkedIn profile"""
   try:
       # Initialize clients
       supabase = create_supabase_client(supabase_url, supabase_key)
       openai_client = OpenAI(api_key=openai_api_key)

       # Check if profile exists
       logger.info(f"Checking if profile {linkedin_url} exists in table {table_name}.")
       existing = check_existing_profile(supabase, linkedin_url, target_company, table_name)
       logger.info(f"Existing profile: {existing}")
       
       if existing == False:
           # Scrape and insert if doesn't exist
           profile = await linkedin_profile_scraper(rapidapi_api_key, linkedin_url)
           if 'error' in profile:
               logger.error(f"Failed to scrape profile: {profile['error']}")
               return
           logger.info("Inserting to db.")
           insert_profiles_to_db(profile, supabase, target_company, table_name)
           logger.info(f"Insertion to {table_name} completed.")
           profile = profile
       else:
           profile = existing["profile_data"]
           logger.info("Profile already exists.")
           return None

       # Updating profile type
       profile_status = await check_profile_status_with_verification(openai_client, profile, auto_approve=True)
       if profile_status is None:
           logger.error("Profile skipped during status check.")
           return None
       
       previous_companies = profile.get("previous_companies", [])
       if target_company in previous_companies:
        logger.info(f"Target company {target_company} found in profile's experience")
        company_of_interest = target_company
       elif target_company not in previous_companies:
        logger.info(f"Target company {target_company} not found. Manual selection required.")
        print("Choose a company of interest.\nAvailable companies:")
        for idx, company in enumerate(previous_companies):
            print(f"{idx + 1}. {company}")
        company_of_interest = input(">")


       role_at_company = extract_company_role(profile, company_of_interest)
       is_senior_operator = check_senior_operator(profile, openai_client)

       is_repeat_founder = False
       is_repeat_founder = check_repeat_founder(profile)

       print(f"Preparing profile with labels with linkedin url: {profile["linkedin_url"]}")

       # Prepare and update labels
       profile_labels = prepare_profile_w_labels(
           is_repeat_founder=is_repeat_founder,
           role_search_company=role_at_company,
           linkedin_url=profile["linkedin_url"],
           is_senior_operator=is_senior_operator,
           profile_status=profile_status, 
           table_name=table_name
       )
        
       print(f"Upating profile labels for: {profile["linkedin_url"]}")

       update_profile_labels(profile_labels, supabase, profile["linkedin_url"], table_name)
       logger.info(f"Pipeline completed successfully")

   except Exception as e:
       logger.error(f"Pipeline failed: {str(e)}")


# ------------------------------


def ensure_trailing_slash(url: str) -> str:
    # Only add slash if it doesn't already end with one
    return url if url.endswith('/') else url + '/'


# ------------------------------


def main():
    try:
        print("Select table:\n1. Current-Employee-Profiles\n2. Unicorn-Stealth-Founder-Profiles")
        choice = input("Enter 1 or 2: ").strip()
        table_name = "Current-Employee-Profiles" if choice == "1" else "Unicorn-Stealth-Founder-Profiles"
        linkedin_url_to_enter = input("Enter LinkedIn URL:")
        target_company_for_reference = input("Enter Company for Reference:")
        # Define list of LinkedIn URLs to process
        linkedin_urls = [
            linkedin_url_to_enter
        ]

        
        total_urls = len(linkedin_urls)
        processed = 0
        failed = 0
        
        logger.info(f"Starting batch processing of {total_urls} profiles")
        
        for index, url in enumerate(linkedin_urls, 1):
            try:
                logger.info(f"\nProcessing profile {index}/{total_urls}: {url}")
                target_company = target_company_for_reference
                url = ensure_trailing_slash(url)
                asyncio.run(process_linkedin_profile(url, target_company, table_name))
                processed += 1
                
            except KeyboardInterrupt:
                logger.info("\nProcess interrupted by user")
                raise  # Re-raise to handle in outer try block
                
            except Exception as e:
                failed += 1
                logger.error(f"Error processing {url}: {str(e)}")
                
                continue_input = input("\nContinue with next profile? (y/n): ").strip().lower()
                if continue_input != 'y':
                    break
        
        # Summary logger
        logger.info(f"\nProcessing complete:")
        logger.info(f"Total profiles: {total_urls}")
        logger.info(f"Successfully processed: {processed}")
        logger.info(f"Failed: {failed}")
                
    except KeyboardInterrupt:
        logger.info("\nProgram terminated by user")
        logger.info(f"Processed {processed}/{total_urls} profiles before termination")
    
    except Exception as e:
        logger.error(f"Fatal error in main pipeline: {str(e)}")


# ------------------------------


if __name__ == "__main__":
    main()