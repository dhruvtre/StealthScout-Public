# StealthScout

A tool for tracking and monitoring talent transitions using LinkedIn data. Monitor when employees leave companies and start new ventures.

## Features

- Track employee status changes (currently employed, recently quit, building in stealth, building in public)
- Identify potential founders and senior operators
- Visualize talent transitions over time

## Repository Structure

* app.py: Main Streamlit application entry point for the web interface
  
* data/data_models.txt: Database schema definitions for Supabase tables
  
* pipelines/: Core data processing scripts
*     insert_profile.py: Add new LinkedIn profiles to database
      profile_refresh.py: Update existing profiles and detect status changes
      profile_status_classifier.py with Examples: AI-powered classification of founder status
      senior_operator_labeller.py with Examples: Identify senior executives
  
* streamlit_app/: UI components and utility functions
*     app_views/: Different views for search, status updates, etc.
      main_functions.py: Common database and processing functions

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see `.env.example`)
4. Set up a Supabase database with the required tables structure as in data_models.txt
5. Get an OpenAI and Fresh LinkedIn Data API keys from links below

## Environment Variables

Create a `.env` file with:

```bash
supabase_url=YOUR_SUPABASE_URL
supabase_key=YOUR_SUPABASE_KEY
rapidapi_api_key=YOUR_RAPIDAPI_KEY
openai_api_key=YOUR_OPENAI_KEY
```
## Usage

### Insert Profiles
This script takes one LinkedIn profile URL and reference company names as input, fetches profile data, classifies it using AI, and adds it to the DB.

```bash
python pipelines/insert_profile.py
```

### Refresh Profiles
Updates existing profiles with fresh data from LinkedIn, detects status changes, and records transitions.

```bash
python pipelines/profile_refresh.py
```

### Run Streamlit App
Launches the web interface with three main views:
- Search Database: Find potential founders from specific companies
- Recent Status Updates: Track recent founder transitions
- Current Employee Search: Monitor employees at target companies

```bash
python streamlit run app.py
```

## APIs Used

1. [Fresh LinkedIn Data API](https://rapidapi.com/freshdata-freshdata-default/api/fresh-linkedin-profile-data) - For fetching profile info
2. [Supabase](https://supabase.com) - Database for storing and querying profiles
3. [OpenAI API](https://platform.openai.com) - For AI-powered profile labelling and classification

## Videos

https://github.com/user-attachments/assets/aa298995-9fa6-491b-a3a6-dd4f1d4fb52e
