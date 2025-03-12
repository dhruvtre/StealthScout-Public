# StealthScout

A tool for tracking and monitoring talent transitions using LinkedIn data. Monitor when employees leave companies and start new ventures.

## Features

- Track employee status changes (currently employed, recently quit, building in stealth, building in public)
- Identify potential founders and senior operators
- Visualize talent transitions over time

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see `.env.example`)
4. Set up a Supabase database with the required tables structure as in data_models.txt
5. Get an OpenAI and Fresh LinkedIn Data API keys from links below

## Environment Variables

Create a `.env` file with:

supabase_url=YOUR_SUPABASE_URL
supabase_key=YOUR_SUPABASE_KEY
rapidapi_api_key=YOUR_RAPIDAPI_KEY
openai_api_key=YOUR_OPENAI_KEY

## Usage

### Insert Profiles

python pipelines/insert_profile.py

### Refresh Profiles

python pipelines/profile_refresh.py

### Run Streamlit App

python streamlit run app.py

## APIs Used

1. [Fresh LinkedIn Data API](https://rapidapi.com/freshdata-freshdata-default/api/fresh-linkedin-profile-data) - For fetching profile info
2. [Supabase](https://supabase.com) - Database for storing and querying profiles
3. [OpenAI API](https://platform.openai.com) - For AI-powered profile labelling and classification