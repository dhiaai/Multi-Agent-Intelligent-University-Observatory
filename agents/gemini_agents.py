"""
gemini_agents.py — AI Career Agents powered by Llama 3.3 70B via Groq
Provides CV generation, cover letter generation, and interview prep.
"""
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def _get_client():
    """Return a Groq client."""
    from groq import Groq
    return Groq(api_key=GROQ_API_KEY)

def _call_llm(prompt):
    """Send a prompt to Llama 3.3 70B via Groq and return the response text."""
    client = _get_client()
    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_completion_tokens=4096,
    )
    return chat.choices[0].message.content


def generate_cv(user_name, user_skills, user_interests, user_profile, opp_title, opp_description, opp_type):
    """Generate an ATS-friendly CV tailored to a specific opportunity."""
    prompt = f"""You are an expert career consultant. Generate a professional, ATS-friendly CV/Resume in clean HTML format.

The CV should be tailored for the following opportunity:
- Opportunity: {opp_title}
- Type: {opp_type}
- Description: {opp_description}

Candidate Information:
- Name: {user_name}
- Profile: {user_profile}
- Skills: {user_skills}
- Interests: {user_interests}

Requirements:
1. Output ONLY the HTML content (no ```html tags, no markdown).
2. Use clean, semantic HTML with inline CSS styles.
3. Use a professional font stack (Arial, Helvetica, sans-serif).
4. Include these sections: Contact Info (use placeholder email/phone), Professional Summary, Education, Skills, Experience (generate plausible entries based on skills), Projects, Certifications.
5. Make it ATS-friendly: no tables for layout, no images, clear headings, standard section names.
6. Use a clean, minimal design with subtle borders and good spacing.
7. The CV should be 1-2 pages when printed.
8. Tailor the professional summary and skills emphasis to match the target opportunity.
"""
    return _call_llm(prompt)


def generate_cover_letter(user_name, user_skills, user_interests, user_profile, opp_title, opp_description, opp_type):
    """Generate a tailored cover letter for a specific opportunity."""
    prompt = f"""You are an expert career consultant. Write a compelling, professional cover letter.

The cover letter is for:
- Opportunity: {opp_title}
- Type: {opp_type}
- Description: {opp_description}

Candidate:
- Name: {user_name}
- Profile: {user_profile}
- Skills: {user_skills}
- Interests: {user_interests}

Requirements:
1. Output ONLY clean HTML (no ```html tags, no markdown).
2. Use inline CSS for styling.
3. Professional business letter format.
4. 3-4 paragraphs: Introduction, Why I'm a great fit (reference specific skills matching the opportunity), What I bring, Closing.
5. Enthusiastic but professional tone.
6. Use a clean, elegant design suitable for printing.
"""
    return _call_llm(prompt)


def generate_interview_prep(user_name, user_skills, user_interests, user_profile, opp_title, opp_description, opp_type):
    """Generate an interview preparation guide for a specific opportunity."""
    prompt = f"""You are an expert career coach. Create a comprehensive interview preparation guide.

The interview is for:
- Opportunity: {opp_title}
- Type: {opp_type}
- Description: {opp_description}

Candidate:
- Name: {user_name}
- Profile: {user_profile}
- Skills: {user_skills}
- Interests: {user_interests}

Requirements:
1. Output ONLY clean HTML (no ```html tags, no markdown).
2. Use inline CSS for styling with a clean, readable design.
3. Include these sections:
   - **Overview**: Brief summary of what to expect
   - **Top 10 Likely Interview Questions** with suggested answer frameworks
   - **Technical Questions** (if applicable based on skills/opportunity type)
   - **Questions to Ask the Interviewer** (5 smart questions)
   - **Key Talking Points**: Specific achievements and skills to highlight
   - **Red Flags to Avoid**: Common mistakes
   - **Preparation Checklist**: Steps to take before the interview
4. Make answers specific to the candidate's background and the opportunity.
5. Use collapsible sections or clear visual hierarchy.
"""
    return _call_llm(prompt)
