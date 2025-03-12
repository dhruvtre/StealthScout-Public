# All necessary imports

import json
import logging
from openai import OpenAI
import random
from typing import Dict
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
import sys
import io

# Basic logging configuration 

import logging
logger = logging.getLogger('stealthscout')

# Load environment variables from the correct path

OPENAI_API_KEY = os.getenv("openai_api_key")
EXAMPLES_PATH = "profile_status_classification_examples.jsonl"

# Defining All Relevant Functions
# 1. Load and Format Profile Status Labelling Examples - load_and_format_examples
# 2. Create Prompt for Status Labelling - create_prompt_with_examples
# 3. Check Profile Status w/ Verification (as necessary) - check_profile_status_with_verification
# 4. Get Single Profile Status - get_profile_status
# 5. main Execution Function w Test Examples - main()
# ------------------------------


def load_and_format_examples(examples_per_status: int = 4) -> str:
    """
    Load examples from profile_status_examples.jsonl and format them for the prompt.
    
    Args:
        examples_per_status: Number of examples to use per status category
    
    Returns:
        Formatted string of examples ready for prompt
    """
    examples_by_status = {
        'stealth': [],
        'building_in_public': [],
        'recently_quit': [],
        'currently_employed': []
    }
    
    # Load and group examples by status
    try:
        with open(EXAMPLES_PATH, 'r') as f:
            for line in f:
                example = json.loads(line)
                status = example.get('assigned_status')
                if status in examples_by_status:
                    examples_by_status[status].append(example)
                    
        logger.info(f"Loaded examples - counts: {[f'{k}: {len(v)}' for k,v in examples_by_status.items()]}")
    except Exception as e:
        logger.error(f"Error loading examples from {EXAMPLES_PATH}: {str(e)}")
        return ""
    
    # Select balanced examples
    selected_examples = []
    for status, examples in examples_by_status.items():
        selected = random.sample(examples, min(examples_per_status, len(examples)))
        selected_examples.extend(selected)
    
    # Format examples
    formatted_examples = []
    for example in selected_examples:
        exp = example['recent_experience']
        formatted = f"""####HEADLINE: {example['headline']}
####EXPERIENCE: {exp['title']} at {exp['company']} ({exp['duration']}, {exp['date_range']})
{example['assigned_status']}"""
        formatted_examples.append(formatted)
    
    return "\n\n".join(formatted_examples)


# ------------------------------


def create_prompt_with_examples(test_profile: Dict) -> str:
    current_time = datetime.now().strftime("%B %d, %Y")
    """Create full prompt with examples and test profile."""
    base_prompt = f"""Today's date: {current_time}
    You are an expert AI assistant classifying LinkedIn profile statuses of startup founders.
The goal is to categorize each profile into one of four statuses AND provide a confidence rating.

OUTPUT FORMAT:
Respond ONLY with: STATUS|CONFIDENCE
Where:
- STATUS must be exactly one of: "stealth", "building_in_public", "recently_quit", "currently_employed"
- CONFIDENCE must be exactly "HIGH" or "LOW"

Mark confidence as LOW if ANY of these are true:
- Missing or ambiguous date information
- Vague or non-standard job titles
- Profile doesn't clearly fit any status criteria
- Limited or incomplete information
- Recent profile changes or transitions
- Contradictory signals between headline and experience

Mark confidence as HIGH only if ALL of these are true:
- Clear, unambiguous status indicators present
- Complete date and duration information
- Standard, recognizable job titles
- Clear company information
- Profile firmly fits one status category
- No contradictory or mixed signals
- Sufficient information available
- Pattern matches known examples

You will be provided with profile data containing:
####HEADLINE: The founder's LinkedIn headline
####EXPERIENCE: Their most recent professional experience including company name, title, duration and date range

Status Classification Criteria:
STEALTH status indicators:
- Company name contains "Stealth", "Stealth Mode" or "Stealth Startup"
- Intentionally vague/minimal information in headline or experience
- Has been unemployed for more than 3 months, or the last experience held was quit about 2-3 months ago. 
- Using terms like "building", "exploring" or "stealth" without naming specific company
- Member of known startup communities (e.g. South Park Commons) while building

BUILDING_IN_PUBLIC status indicators:
- Clear company name which is that of a startup and not a large existing company
- Openly stating what they're building in headline
- Detailed founder title at named company
- The role is Founder in a company you are not familiar with. 
- The role of Founder is their current role. 
- Actively describing product/mission
- Using terms like "building" or "founder at [Named Company]" or "CEO at [Named Company]"

RECENTLY_QUIT status indicators:
- Most recent role has an end date within past 3 months
- "Ex-" or "Former" in headline
- Gap since last full-time role relative to today
- Short duration in most recent role
- Interim/transitional roles or self-employed
- The last experience has ended within past 90-120 days.

CURRENTLY_EMPLOYED status indicators:
- Active full-time role at established company (not startup)
- Standard corporate title (Director, VP, etc.)
- No founder/entrepreneurial signals
- Clear ongoing employment (no end date)
- Regular corporate role patterns

Here are some examples with their classifications:
"""
    # Add examples
    examples_text = load_and_format_examples()
    # Add test profile
    most_recent_exp = test_profile['experience'][0]
    test_profile_text = f"""####HEADLINE: {test_profile.get('headline', '')}
    ####EXPERIENCE: {most_recent_exp['title']} at {most_recent_exp['company']} ({most_recent_exp['duration']}, {most_recent_exp['date_range']})"""
    return base_prompt + examples_text + "\n\nClassify this profile with status and confidence:\n" + test_profile_text


# ------------------------------


async def check_profile_status_with_verification(client: OpenAI, profile: Dict, auto_approve: bool = False, old_status: str = None) -> Dict:
    """
    Gets AI classification for profile status, verifies with user, and optionally saves examples.
    
    Args:
        client: OpenAI client
        profile: Dict containing profile information
        
    Returns:
        Dict with keys:
            - status: Verified profile status
            - confidence_label: Confidence level of classification
    """
    try:
        # Get AI classification
        ai_result = get_profile_status(client, profile)
        new_status = ai_result['status']
        logger.info(f"New Status: {new_status}")
        logger.info(f"Old Status: {old_status}")

        # Only auto-approve if status is unchanged
        status_unchanged = (old_status == new_status)
        should_auto_approve = auto_approve and status_unchanged

        # If auto_approve is True, skip verification
        if should_auto_approve:
            logger.info(f"Auto-approving status (non-critical changes only, status remains: {new_status})")
            return {
                "status": ai_result['status'],
                "confidence_label": ai_result['confidence_label']
            } 
        
        if auto_approve and not status_unchanged:
            logger.info(f"Manual verification required despite non-critical changes (status would change: {old_status} → {new_status})")
        
        # Show profile for verification
        print("\nProfile Review:")
        print("-" * 50)
        print(f"Name: {profile.get('full_name')}")
        print(f"Headline: {profile.get('headline')}")
        
        if profile.get('experience'):
            recent_exp = profile['experience'][0]
            print("\nMost Recent Experience:")
            print(f"Title: {recent_exp.get('title')}")
            print(f"Company: {recent_exp.get('company')}")
            print(f"Duration: {recent_exp.get('duration')}")
            print(f"Date Range: {recent_exp.get('date_range')}")
        
        print(f"\nAI Classification: {ai_result['status']} (Confidence: {ai_result['confidence_label']})")
        
        # Get verification
        is_correct = input("\nIs this classification correct? (y/n): ").strip().lower()
        
        if is_correct == 'y':
            final_status = ai_result['status']
            save_example = input("Save this as a training example? (y/n): ").strip().lower()
            
            if save_example == 'y':
                example = {
                    "headline": profile.get('headline'),
                    "recent_experience": profile.get('experience', [])[0] if profile.get('experience') else {},
                    "assigned_status": final_status,
                    "timestamp": datetime.now().isoformat()
                }
                with open('profile_status_classification_examples.jsonl', 'a') as f:
                    f.write(json.dumps(example) + '\n')
                logging.info("Saved as training example")
        else:
            print("\nValid statuses: currently_employed, stealth, building_in_public, recently_quit")
            final_status = input("Enter correct status: ").strip().lower()
            save_incorrect = input("Save this correction as a training example? (y/n): ").strip().lower()
            
            if save_incorrect == 'y':
                example = {
                    "headline": profile.get('headline'),
                    "recent_experience": profile.get('experience', [])[0] if profile.get('experience') else {},
                    "assigned_status": final_status,
                    "timestamp": datetime.now().isoformat()
                }
                with open('profile_status_classification_examples.jsonl', 'a') as f:
                    f.write(json.dumps(example) + '\n')
                logger.info("Saved correction as training example")
        
        return {
            "status": final_status,
            "confidence_label": ai_result['confidence_label']
        }
        
    except Exception as e:
        logger.error(f"Error in profile status verification: {str(e)}")
        return {"status": None, "confidence_label": "low"}


# ------------------------------


def get_profile_status(client: OpenAI, test_profile: Dict) -> Dict:
    """
    Get status prediction and confidence from OpenAI.
    
    Args:
        client: OpenAI client instance
        test_profile: Dict containing profile data with headline and experience
    
    Returns:
        Dict containing:
            - status (str): 'stealth', 'building_in_public', or 'recently_quit'
            - confidence_label (str): 'high' or 'low'
    """
    try:
        prompt = create_prompt_with_examples(test_profile)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.6
        )
        
        # Parse response (expecting format: "status|confidence")
        response_text = response.choices[0].message.content.strip().lower()
        status, confidence_label = response_text.split('|')
        
        return {
            "status": status.strip(),
            "confidence_label": confidence_label.strip()
        }
            
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return {
            "status": "",
            "confidence_label": "low"
        }

if __name__ == "__main__":
    test_profiles = [
   # Clear currently_employed
   {
       "headline": "Director of Engineering at Swiggy",
       "experience": [{
           "title": "Director of Engineering",
           "company": "Swiggy",
           "duration": "6 yrs 2 mos",
           "date_range": "Oct 2018 - Present"
       }]
   },
   # Recently quit
   {
       "headline": "Previously Engineering Director @Swiggy | Taking a break",
       "experience": [{
           "title": "Engineering Director",
           "company": "Swiggy",
           "duration": "5 yrs 8 mos",
           "date_range": "Apr 2019 - Nov 2024" 
       }]
   },
   # Clear stealth
   {
       "headline": "Building something new in AI",
       "experience": [{
           "title": "Founder",
           "company": "Stealth Mode",
           "duration": "3 mos",
           "date_range": "Sep 2024 - Present"
       }]
   },
   # Building in public
   {
       "headline": "Founder & CEO at DataStack - Building next-gen analytics",
       "experience": [{
           "title": "Founder & CEO",
           "company": "DataStack",
           "duration": "4 mos",
           "date_range": "Aug 2024 - Present"
       }]
   },
   # Edge: Ambiguous duration
   {
       "headline": "Engineering @ Stealth Startup",
       "experience": [{
           "title": "Engineering Lead",
           "company": "Stealth",
           "duration": "1 mo",
           "date_range": "Nov 2024 - Present"
       }]
   },
   # Edge: Multiple signals
   {
       "headline": "Advisor & Mentor | Ex-Swiggy | Working on something new",
       "experience": [{
           "title": "Independent Advisor",
           "company": "Self Employed",
           "duration": "2 mos",
           "date_range": "Oct 2024 - Present"
       }]
   },
   # Edge: Vague status
   {
       "headline": "Engineering Leader | AI Enthusiast",
       "experience": [{
           "title": "Engineering Manager",
           "company": "Undisclosed",
           "duration": "5 mos",
           "date_range": "Jul 2024 - Present"
       }]
   },
   # Edge: Recent transition
   {
       "headline": "Co-founder at NewCo (Coming Soon!) | Ex-Swiggy",
       "experience": [{
           "title": "Co-founder",
           "company": "NewCo",
           "duration": "2 weeks",
           "date_range": "Dec 2024 - Present"
       }]
   },
   # Currently employed but potential signal
   {
       "headline": "Director of Product at Swiggy | Angel Investor",
       "experience": [{
           "title": "Director of Product",
           "company": "Swiggy",
           "duration": "7 yrs",
           "date_range": "Dec 2017 - Present"
       }]
   },
   # Edge: Long gap
   {
       "headline": "Ex-VP Engineering at Swiggy | Exploring Next Steps",
       "experience": [{
           "title": "VP Engineering",
           "company": "Swiggy",
           "duration": "6 yrs",
           "date_range": "Jan 2018 - Aug 2024"
       }]
   }
]

    client = OpenAI(api_key=OPENAI_API_KEY)
    for profile in test_profiles:
        result = get_profile_status(client, profile)
        print(f"\nProfile: {profile['headline']}")
        print(f"Classification: {result['status']} ({result['confidence_label']})")