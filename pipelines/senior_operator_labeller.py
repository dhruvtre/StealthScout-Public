# All necessary imports

import json

# Basic logging configuration 

import logging
logger = logging.getLogger('stealthscout')

# Load environment variables from the correct path

# Load pre-labeled examples from the JSON file
with open('senior_operator_labelling_examples.json', 'r') as f:
    labeled_examples = json.load(f)

# Defining All Relevant Functions
# 1. Prompt for Labelling Senior Operator - senior_operator_labelling_prompt
# 2. Functing to Call for Senior Operator Labelling w/ Examples - senior_operator_labelling_call
# ------------------------------


senior_operator_labelling_prompt = '''You are a helpful AI assistant acting as an investment analyst reviewing LinkedIn profiles of stealth founders to label them as “senior operators” or not.

The goal is to arrive at an accurate label to decide if we should reach out to this founder to initiate an investment discussion.

You will be provided with a ####LINKEDIN PROFILE for each founder, including their professional work experience, job titles, companies, and durations for each role.

Review their work experience and determine if they can be classified as “senior operators” based on the following criteria:

	•	Has 10 or more years of total professional experience (consider the most recent 15 years).
	•	Has held leadership positions such as Director, Head, AVP, Senior Manager, Vice President, CTO, or Founder.
	•	Demonstrates a clear career progression into roles with increasing responsibility.
	•	Has founded or worked in prominent companies with signficant impact (e.g., Fortune 500, industry leader companies, companies with significant funding or companies with notable market presence.)
	•	Has spent enough time in roles to be able to show sustained impact and has not jumped from role to role too often. 
	•	Shows notable achievements or contributions to the industry, such as awards, patents, or leading projects resulting in substantial growth.

Label the profile as “TRUE” if the individual meets at least four of the above criteria.

Your final output should only include “TRUE” or “FALSE” without any additional text or explanation.'''


# ------------------------------


def senior_operator_labelling_call(client, profile, examples, max_examples=10):
    """
    Makes an API call to OpenAI to predict whether a profile qualifies as a 'Senior Operator.'

    Parameters:
    - client: OpenAI client
    - profile: dict, The profile containing experience data.
    - examples: list, A list of already labeled examples (labeled_senior_operator_profiles.json).
    - max_examples: int, The maximum number of examples to include in the prompt (default is 5).

    Returns:
    - str: The AI's prediction for 'is_senior_operator'.
    """
    try:
        # Prepare messages with system prompt
        messages = [{"role": "system", "content": senior_operator_labelling_prompt}]

        # Add a limited number of labeled examples to the conversation (e.g., 5 examples)
        for example in examples[:max_examples]:
            example_experience = "\n".join([f"- {exp['title']} at {exp['company']} for {exp['duration']}" for exp in example['experience']])
            example_text = f"Profile: {example['full_name']}\nExperience:\n{example_experience}"
            messages.append({"role": "user", "content": example_text})
            messages.append({"role": "assistant", "content": f"{example['is_senior_operator']}"})

        # Add the profile in question
        profile_experience = "\n".join([f"- {exp['title']} at {exp['company']} for {exp['duration']}" for exp in profile['experience']])
        profile_text = f"Profile: {profile.get('full_name', 'Unknown Name')}\nExperience:\n{profile_experience}"
        messages.append({"role": "user", "content": profile_text})

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        # Extract the AI's prediction
        print(response)
        ai_response = response.choices[0].message.content.strip()
        return ai_response

    except Exception as e:
        logger.error(f"Error during LLM call: {str(e)}")
        return None