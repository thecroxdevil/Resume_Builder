import streamlit as st
import os
import google.generativeai as genai
import json
from openai import OpenAI

# Configuration and setup
st.set_page_config(page_title="AI Resume Customizer", layout="wide")

# Initialize session state variables if they don't exist
if 'resume_prompt' not in st.session_state:
    st.session_state.resume_prompt = """
    You are a professional resume writer. Your task is to customize the provided resume template to match the job description.
    Follow these guidelines:
    1. Keep the LaTeX format exactly as is
    2. Only modify content sections, not the formatting commands
    3. Highlight relevant skills and experiences from the resume that match the job description
    4. Be concise and professional
    5. Maintain the same overall structure
    6. Return ONLY the modified LaTeX code
    """

if 'cover_letter_prompt' not in st.session_state:
    st.session_state.cover_letter_prompt = """
    Create a professional cover letter based on the provided resume and job description. 
    Follow these guidelines:
    1. Keep the LaTeX format exactly as is
    2. Only modify content sections, not the formatting commands
    3. Highlight how the candidate's skills and experiences directly relate to the job requirements
    4. Be persuasive, confident, and professional
    5. Return ONLY the modified LaTeX code
    """

# Function to load templates from disk
def load_template(template_type):
    try:
        file_path = f"templates/{template_type}_template.tex"
        with open(file_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

# Function to save templates to disk
def save_template(template_type, content):
    os.makedirs("templates", exist_ok=True)
    with open(f"templates/{template_type}_template.tex", "w") as f:
        f.write(content)

# Function to save prompts
def save_prompts():
    os.makedirs("prompts", exist_ok=True)
    prompts = {
        "resume_prompt": st.session_state.resume_prompt,
        "cover_letter_prompt": st.session_state.cover_letter_prompt
    }
    with open("prompts/saved_prompts.json", "w") as f:
        json.dump(prompts, f)

# Function to load prompts
def load_prompts():
    try:
        with open("prompts/saved_prompts.json", "r") as f:
            prompts = json.load(f)
            st.session_state.resume_prompt = prompts.get("resume_prompt", st.session_state.resume_prompt)
            st.session_state.cover_letter_prompt = prompts.get("cover_letter_prompt", st.session_state.cover_letter_prompt)
    except FileNotFoundError:
        pass

# Initialize Gemini API
@st.cache_resource
def initialize_gemini_api():
    try:
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    except Exception as e:
        st.error(f"Error initializing Gemini API: {e}")

# Initialize OpenRouter Client for DeepSeek
@st.cache_resource
def initialize_openrouter_client():
    try:
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
    except Exception as e:
        st.error(f"Error initializing OpenRouter client: {e}")
        return None

initialize_gemini_api()

# Function to customize resume with Gemini
def customize_resume(resume_template, job_description, prompt):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            f"{prompt}\n\nJob Description:\n{job_description}\n\nResume Template:\n{resume_template}"
        )
        return response.text
    except Exception as e:
        st.error(f"Error customizing resume with Gemini: {e}")
        return None

# Function to generate cover letter with Gemini
def generate_cover_letter(resume, job_description, prompt, template):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            f"{prompt}\n\nJob Description:\n{job_description}\n\nResume:\n{resume}\n\nCover Letter Template:\n{template}"
        )
        return response.text
    except Exception as e:
        st.error(f"Error generating cover letter with Gemini: {e}")
        return None

# Function to customize resume with DeepSeek
def customize_resume_deepseek(resume_template, job_description, prompt):
    try:
        client = initialize_openrouter_client()
        if not client:
            return None
        
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://yourappdomain.com",  # Update with your actual domain
                "X-Title": "AI Resume Customizer",
            },
            model="deepseek/deepseek-r1:free",
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nJob Description:\n{job_description}\n\nResume Template:\n{resume_template}"
                }
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"Error customizing resume with DeepSeek: {e}")
        return None

# Function to generate cover letter with DeepSeek
def generate_cover_letter_deepseek(resume, job_description, prompt, template):
    try:
        client = initialize_openrouter_client()
        if not client:
            return None
            
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://yourappdomain.com",  # Update with your actual domain
                "X-Title": "AI Resume Customizer",
            },
            model="deepseek/deepseek-r1:free",
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nJob Description:\n{job_description}\n\nResume:\n{resume}\n\nCover Letter Template:\n{template}"
                }
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating cover letter with DeepSeek: {e}")
        return None

# Load saved prompts on app startup
load_prompts()

# UI Header
st.title("AI Resume & Cover Letter Customizer")

# Sidebar for templates and prompt settings
with st.sidebar:
    st.header("Templates & Settings")
    
    # Template management
    st.subheader("Resume Template")
    
    template_option = st.radio(
        "Resume Template Option:",
        ["Use saved template", "Upload new template"]
    )
    
    if template_option == "Upload new template":
        resume_template_file = st.file_uploader("Upload Resume LaTeX Template", type=["tex"])
        if resume_template_file is not None:
            resume_template = resume_template_file.getvalue().decode("utf-8")
            save_template("resume", resume_template)
            st.success("Resume template saved!")
        else:
            resume_template = load_template("resume")
    else:
        resume_template = load_template("resume")
        if not resume_template:
            st.warning("No saved resume template found. Please upload one.")
    
    st.subheader("Cover Letter Template")
    
    cl_template_option = st.radio(
        "Cover Letter Template Option:",
        ["Use saved template", "Upload new template"]
    )
    
    if cl_template_option == "Upload new template":
        cl_template_file = st.file_uploader("Upload Cover Letter LaTeX Template", type=["tex"])
        if cl_template_file is not None:
            cl_template = cl_template_file.getvalue().decode("utf-8")
            save_template("cover_letter", cl_template)
            st.success("Cover letter template saved!")
        else:
            cl_template = load_template("cover_letter")
    else:
        cl_template = load_template("cover_letter")
        if not cl_template:
            st.warning("No saved cover letter template found. Please upload one.")
    
    # Prompt management
    st.subheader("AI Prompts")
    
    st.text_area("Resume Customization Prompt", value=st.session_state.resume_prompt, 
                height=200, key="resume_prompt_input", 
                on_change=lambda: setattr(st.session_state, "resume_prompt", st.session_state.resume_prompt_input))
    
    st.text_area("Cover Letter Generation Prompt", value=st.session_state.cover_letter_prompt, 
                height=200, key="cl_prompt_input", 
                on_change=lambda: setattr(st.session_state, "cover_letter_prompt", st.session_state.cl_prompt_input))
    
    if st.button("Save Prompts"):
        st.session_state.resume_prompt = st.session_state.resume_prompt_input
        st.session_state.cover_letter_prompt = st.session_state.cl_prompt_input
        save_prompts()
        st.success("Prompts saved!")
        
    # AI Model Selection
    st.subheader("AI Model Selection")
    ai_model = st.selectbox(
        "Select AI Model:",
        ["Google Gemini", "DeepSeek (via OpenRouter)"]
    )
    
    # API key input (for local development)
    st.subheader("API Settings")
    google_api_key = st.text_input("Google API Key", type="password")
    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key
        
    openrouter_api_key = st.text_input("OpenRouter API Key (for DeepSeek)", type="password")
    if openrouter_api_key:
        os.environ["OPENROUTER_API_KEY"] = openrouter_api_key

# Main area
st.header("Job Description Input")
job_description = st.text_area("Paste the job description here:", height=300)

if st.button("Generate Customized Documents") and job_description:
    if not resume_template:
        st.error("Please upload or select a resume template first.")
    elif not cl_template:
        st.error("Please upload or select a cover letter template first.")
    else:
        with st.spinner("Customizing resume..."):
            if ai_model == "Google Gemini":
                customized_resume = customize_resume(resume_template, job_description, st.session_state.resume_prompt)
            else:  # DeepSeek
                customized_resume = customize_resume_deepseek(resume_template, job_description, st.session_state.resume_prompt)
        
        if customized_resume:
            st.session_state.customized_resume = customized_resume
            
            with st.spinner("Generating cover letter..."):
                if ai_model == "Google Gemini":
                    cover_letter = generate_cover_letter(
                        customized_resume, 
                        job_description, 
                        st.session_state.cover_letter_prompt,
                        cl_template
                    )
                else:  # DeepSeek
                    cover_letter = generate_cover_letter_deepseek(
                        customized_resume, 
                        job_description, 
                        st.session_state.cover_letter_prompt,
                        cl_template
                    )
            
            if cover_letter:
                st.session_state.cover_letter = cover_letter
                st.success("Documents generated successfully!")
            else:
                st.error("Failed to generate cover letter.")
        else:
            st.error("Failed to customize resume.")

# Display results in tabs
if 'customized_resume' in st.session_state and 'cover_letter' in st.session_state:
    tab1, tab2 = st.tabs(["Customized Resume", "Cover Letter"])
    
    with tab1:
        st.subheader("Customized Resume (LaTeX)")
        st.code(st.session_state.customized_resume, language="latex")
        
        if st.button("Regenerate Resume"):
            with st.spinner("Customizing resume..."):
                if ai_model == "Google Gemini":
                    customized_resume = customize_resume(resume_template, job_description, st.session_state.resume_prompt)
                else:  # DeepSeek
                    customized_resume = customize_resume_deepseek(resume_template, job_description, st.session_state.resume_prompt)
            if customized_resume:
                st.session_state.customized_resume = customized_resume
                st.rerun()
        
        # Download button for resume
        resume_download = st.download_button(
            label="Download Resume LaTeX",
            data=st.session_state.customized_resume,
            file_name="customized_resume.tex",
            mime="text/plain"
        )
    
    with tab2:
        st.subheader("Cover Letter (LaTeX)")
        st.code(st.session_state.cover_letter, language="latex")
        
        if st.button("Regenerate Cover Letter"):
            with st.spinner("Generating cover letter..."):
                if ai_model == "Google Gemini":
                    cover_letter = generate_cover_letter(
                        st.session_state.customized_resume, 
                        job_description, 
                        st.session_state.cover_letter_prompt,
                        cl_template
                    )
                else:  # DeepSeek
                    cover_letter = generate_cover_letter_deepseek(
                        st.session_state.customized_resume, 
                        job_description, 
                        st.session_state.cover_letter_prompt,
                        cl_template
                    )
            if cover_letter:
                st.session_state.cover_letter = cover_letter
                st.rerun()
        
        # Download button for cover letter
        cl_download = st.download_button(
            label="Download Cover Letter LaTeX",
            data=st.session_state.cover_letter,
            file_name="cover_letter.tex",
            mime="text/plain"
        )
