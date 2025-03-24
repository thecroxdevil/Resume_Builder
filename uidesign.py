import streamlit as st
import os
import google.generativeai as genai
import json
from openai import OpenAI

# Configuration and setup
st.set_page_config(page_title="AI Resume Customizer", layout="wide")

# Add this near the top of your file after st.set_page_config
# Custom CSS to make the sidebar hideable
st.markdown("""
<style>
    /* Hide the default sidebar toggle */
    .css-1rs6os.edgvbvh3 {
        visibility: hidden;
    }
    
    /* Create a custom sidebar toggle button */
    .sidebar-toggle {
        position: fixed;
        top: 60px;
        left: 0;
        z-index: 99;
        padding: 4px 10px;
        background: #4e8cff;
        color: white;
        border-radius: 0 4px 4px 0;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.3s;
    }
    
    /* JavaScript to toggle sidebar visibility */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>

<script>
    // Add toggle button to the page
    document.addEventListener('DOMContentLoaded', function() {
        const sidebarToggle = document.createElement('div');
        sidebarToggle.className = 'sidebar-toggle';
        sidebarToggle.innerHTML = '◀';
        sidebarToggle.title = 'Toggle Sidebar';
        document.body.appendChild(sidebarToggle);
        
        let sidebarHidden = false;
        const sidebar = document.querySelector('.css-1d391kg, .css-1lcbmhc');
        
        sidebarToggle.addEventListener('click', function() {
            if (sidebarHidden) {
                sidebar.style.margin = '0px';
                sidebar.style.width = '260px';
                sidebar.style.opacity = '1';
                sidebarToggle.innerHTML = '◀';
                sidebarHidden = false;
            } else {
                sidebar.style.margin = '0 0 0 -260px';
                sidebar.style.width = '0px';
                sidebar.style.opacity = '0';
                sidebarToggle.innerHTML = '▶';
                sidebarHidden = true;
            }
        });
    });
</script>
""", unsafe_allow_html=True)


# Custom CSS to make it look more like your HTML design
st.markdown("""
<style>
    /* Chat container styling */
    .main .block-container {
        max-width: 800px !important;
        padding-top: 2rem;
        padding-bottom: 0;
    }
    
    /* Chat message styling */
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e6f2ff;
        border-left: 4px solid #2196F3;
    }
    .ai-message {
        background-color: #f0f0f0;
        border-left: 4px solid #4CAF50;
    }
    
    /* Message header styling */
    .message-header {
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    /* Chat input styling */
    .stTextInput>div>div>input {
        border: none !important;
        padding: 12px !important;
        font-size: 16px !important;
    }
    
    /* Selectbox styling */
    .stSelectbox>div>div {
        background-color: #f9f9f9 !important;
    }
    
    /* Buttons styling */
    .stButton>button {
        border-radius: 20px;
        padding: 5px 15px;
    }
    
    /* Dataframe without index */
    .dataframe-container [data-testid="stDataFrame"] td:first-child {
        display: none;
    }
    .dataframe-container [data-testid="stDataFrame"] th:first-child {
        display: none;
    }
    
    /* Hide hamburger menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Template and settings panel */
    .css-1544g2n {
        padding: 1rem;
        margin-top: 0;
    }
</style>
""", unsafe_allow_html=True)

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

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "current_mode" not in st.session_state:
    st.session_state.current_mode = "job_description"

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
        return True
    except Exception as e:
        st.error(f"Error initializing Gemini API: {e}")
        return False

# Initialize OpenRouter Client
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

# Initialize APIs on app startup
gemini_initialized = initialize_gemini_api()

# Function to customize resume with Gemini
def customize_resume(resume_template, job_description, prompt):
    try:
        if not gemini_initialized:
            st.error("Gemini API not properly initialized. Check API key in Hugging Face Secrets.")
            return None
            
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
        if not gemini_initialized:
            st.error("Gemini API not properly initialized. Check API key in Hugging Face Secrets.")
            return None
            
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
            st.error("OpenRouter client not properly initialized. Check API key in Hugging Face Secrets.")
            return None
        
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://yourappdomain.com",
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
            st.error("OpenRouter client not properly initialized. Check API key in Hugging Face Secrets.")
            return None
            
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://yourappdomain.com",
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

# Function to add chat message
def add_chat_message(sender, content, message_type="text"):
    st.session_state.chat_messages.append({
        "sender": sender,
        "content": content,
        "type": message_type
    })

# Main Application UI
st.title("AI Resume & Cover Letter Customizer")

# Create two columns - one for chat and one for settings
col1, col2 = st.columns([3, 1])

with col2:
    with st.expander("Settings & Templates", expanded=True):
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
        with st.subheader("Edit AI Prompts"):
            st.text_area("Resume Customization Prompt", value=st.session_state.resume_prompt, 
                        height=150, key="resume_prompt_input", 
                        on_change=lambda: setattr(st.session_state, "resume_prompt", st.session_state.resume_prompt_input))
        
            st.text_area("Cover Letter Generation Prompt", value=st.session_state.cover_letter_prompt, 
                        height=150, key="cl_prompt_input", 
                        on_change=lambda: setattr(st.session_state, "cover_letter_prompt", st.session_state.cl_prompt_input))
        
            if st.button("Save Prompts"):
                st.session_state.resume_prompt = st.session_state.resume_prompt_input
                st.session_state.cover_letter_prompt = st.session_state.cl_prompt_input
                save_prompts()
                st.success("Prompts saved!")

        # API status indicators
        st.subheader("API Status")
        
        if os.environ.get("GOOGLE_API_KEY"):
            st.success("Google API Key: ✓")
        else:
            st.error("Google API Key: ✗")
            
        if os.environ.get("OPENROUTER_API_KEY"):
            st.success("OpenRouter API Key: ✓")
        else:
            st.error("OpenRouter API Key: ✗")

with col1:
    # Chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat messages
        for message in st.session_state.chat_messages:
            if message["sender"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <div class="message-header">You:</div>
                    <div>{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message ai-message">
                    <div class="message-header">{message["sender"]}:</div>
                    <div>{message["content"] if message["type"] == "text" else "Generated Document (See Downloads)"}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Add download buttons for generated documents
                if message["type"] == "resume":
                    st.download_button(
                        "Download Resume",
                        message["content"],
                        file_name="customized_resume.tex",
                        mime="text/plain"
                    )
                elif message["type"] == "cover_letter":
                    st.download_button(
                        "Download Cover Letter",
                        message["content"],
                        file_name="cover_letter.tex",
                        mime="text/plain"
                    )

    # Input area
    st.markdown("<hr>", unsafe_allow_html=True)
    
    if st.session_state.current_mode == "job_description":
        st.markdown("### Step 1: Enter the job description")
        job_description = st.text_area("", height=150, placeholder="Paste the job description here...", label_visibility="collapsed")
        
        if st.button("Continue"):
            if job_description:
                add_chat_message("user", job_description)
                st.session_state.job_description = job_description
                st.session_state.current_mode = "generate_documents"
                st.rerun()
            else:
                st.error("Please enter a job description.")
                
    elif st.session_state.current_mode == "generate_documents":
        # Model selection and generation
        col_model, col_generate = st.columns([1, 3])
        
        with col_model:
            ai_model = st.selectbox(
                "",
                ["Google Gemini", "DeepSeek"],
                label_visibility="collapsed"
            )
            
        with col_generate:
            if st.button("Generate Resume & Cover Letter"):
                if not resume_template:
                    st.error("Please upload a resume template first.")
                elif not cl_template:
                    st.error("Please upload a cover letter template first.")
                else:
                    with st.spinner("Working on your documents..."):
                        # Generate customized resume
                        if ai_model == "Google Gemini":
                            customized_resume = customize_resume(
                                resume_template, 
                                st.session_state.job_description, 
                                st.session_state.resume_prompt
                            )
                        else:  # DeepSeek
                            customized_resume = customize_resume_deepseek(
                                resume_template, 
                                st.session_state.job_description, 
                                st.session_state.resume_prompt
                            )
                        
                        if customized_resume:
                            # Save resume to session state and add to chat
                            st.session_state.customized_resume = customized_resume
                            add_chat_message(ai_model, customized_resume, "resume")
                            
                            # Generate cover letter
                            if ai_model == "Google Gemini":
                                cover_letter = generate_cover_letter(
                                    customized_resume, 
                                    st.session_state.job_description, 
                                    st.session_state.cover_letter_prompt,
                                    cl_template
                                )
                            else:  # DeepSeek
                                cover_letter = generate_cover_letter_deepseek(
                                    customized_resume, 
                                    st.session_state.job_description, 
                                    st.session_state.cover_letter_prompt,
                                    cl_template
                                )
                            
                            if cover_letter:
                                # Save cover letter to session state and add to chat
                                st.session_state.cover_letter = cover_letter
                                add_chat_message(ai_model, cover_letter, "cover_letter")
                                
                                # Add success message
                                add_chat_message(ai_model, "Your resume and cover letter have been generated successfully! You can download them using the buttons above.", "text")
                                
                                # Reset to allow new job descriptions
                                st.session_state.current_mode = "job_description"
                                st.rerun()
                            else:
                                st.error("Failed to generate cover letter.")
                        else:
                            st.error("Failed to customize resume.")
            
            if st.button("Start Over"):
                st.session_state.current_mode = "job_description"
                st.rerun()
