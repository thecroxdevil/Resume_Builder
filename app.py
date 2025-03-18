import os
import json
import gradio as gr
import google.generativeai as genai
from openai import OpenAI
import tempfile
import time
from pathlib import Path
from datetime import datetime

# Theme and styling with Perplexity-like interface
custom_css = """
:root {
    --main-bg-color: #ffffff;
    --sidebar-bg-color: #f9f9fa;
    --accent-color: #6c5ce7;
    --text-color: #0f172a;
    --border-color: #e2e8f0;
    --hover-color: #f1f5f9;
}

body, .gradio-container {
    background-color: var(--main-bg-color) !important;
    color: var(--text-color);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.header {
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 12px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.hidden-settings {
    position: fixed;
    top: 0;
    right: 0;
    width: 0;
    height: 100%;
    background-color: var(--sidebar-bg-color);
    overflow-x: hidden;
    transition: 0.3s;
    z-index: 100;
    padding: 0;
    box-shadow: -2px 0 8px rgba(0,0,0,0.1);
}

.hidden-settings.open {
    width: 400px;
    padding: 24px;
}

.settings-toggle {
    cursor: pointer;
    padding: 8px 12px;
    border-radius: 4px;
    color: var(--text-color);
    display: flex;
    align-items: center;
    gap: 8px;
}

.settings-toggle:hover {
    background-color: var(--hover-color);
}

.central-search {
    max-width: 800px;
    margin: 80px auto 40px;
    text-align: center;
}

.central-search h1 {
    font-size: 28px;
    margin-bottom: 24px;
    font-weight: 600;
}

.search-bar {
    border: 1px solid var(--border-color);
    border-radius: 24px;
    padding: 16px 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    display: flex;
    align-items: center;
    background-color: var(--main-bg-color);
}

.search-bar:focus-within {
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    border-color: var(--accent-color);
}

.result-container {
    max-width: 800px;
    margin: 30px auto;
    padding: 24px;
    border-radius: 12px;
    border: 1px solid var(--border-color);
    background-color: var(--main-bg-color);
}

.model-select {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    justify-content: center;
}

.model-option {
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 14px;
    cursor: pointer;
    background-color: var(--main-bg-color);
}

.model-option.selected {
    background-color: var(--accent-color);
    color: white;
    border-color: var(--accent-color);
}

.answer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
}

.source-citation {
    display: inline-block;
    background-color: rgba(108, 92, 231, 0.1);
    color: var(--accent-color);
    font-size: 12px;
    border-radius: 4px;
    padding: 2px 6px;
    margin: 0 2px;
    cursor: pointer;
}

.source-list {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--border-color);
}

.source-item {
    padding: 8px 12px;
    border-radius: 8px;
    margin-bottom: 8px;
    background-color: var(--hover-color);
}

.action-button {
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 14px;
    cursor: pointer;
    background-color: var(--main-bg-color);
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-right: 8px;
}

.action-button:hover {
    background-color: var(--hover-color);
}

.action-button.primary {
    background-color: var(--accent-color);
    color: white;
    border-color: var(--accent-color);
}

.related-questions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 16px;
}

.related-question {
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 14px;
    cursor: pointer;
    background-color: var(--main-bg-color);
}

.related-question:hover {
    background-color: var(--hover-color);
}

.hidden {
    display: none;
}

.settings-section {
    margin-bottom: 24px;
}

.settings-section h3 {
    font-size: 16px;
    margin-bottom: 12px;
    font-weight: 600;
}

.close-settings {
    position: absolute;
    top: 20px;
    right: 20px;
    cursor: pointer;
    font-size: 24px;
}

.footer {
    text-align: center;
    padding: 20px 0;
    color: #94a3b8;
    font-size: 14px;
    border-top: 1px solid var(--border-color);
    margin-top: 40px;
}
"""

# Configuration constants
DEFAULT_RESUME_PROMPT = """
You are a professional resume writer. Your task is to customize the provided resume template to match the job description.
Follow these guidelines:
1. Keep the LaTeX format exactly as is
2. Only modify content sections, not the formatting commands
3. Highlight relevant skills and experiences from the resume that match the job description
4. Be concise and professional
5. Maintain the same overall structure
6. Return ONLY the modified LaTeX code
"""

DEFAULT_COVER_LETTER_PROMPT = """
Create a professional cover letter based on the provided resume and job description. 
Follow these guidelines:
1. Keep the LaTeX format exactly as is
2. Only modify content sections, not the formatting commands
3. Highlight how the candidate's skills and experiences directly relate to the job requirements
4. Be persuasive, confident, and professional
5. Return ONLY the modified LaTeX code
"""

# File handling functions
def ensure_directory(directory):
    Path(directory).mkdir(parents=True, exist_ok=True)

def load_template(template_type):
    try:
        file_path = f"templates/{template_type}_template.tex"
        with open(file_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def save_template(template_type, content):
    ensure_directory("templates")
    with open(f"templates/{template_type}_template.tex", "w") as f:
        f.write(content)
    return True

def load_prompts():
    try:
        with open("prompts/saved_prompts.json", "r") as f:
            prompts = json.load(f)
            return prompts.get("resume_prompt", DEFAULT_RESUME_PROMPT), prompts.get("cover_letter_prompt", DEFAULT_COVER_LETTER_PROMPT)
    except FileNotFoundError:
        return DEFAULT_RESUME_PROMPT, DEFAULT_COVER_LETTER_PROMPT

def save_prompts(resume_prompt, cover_letter_prompt):
    ensure_directory("prompts")
    prompts = {
        "resume_prompt": resume_prompt,
        "cover_letter_prompt": cover_letter_prompt
    }
    with open("prompts/saved_prompts.json", "w") as f:
        json.dump(prompts, f)
    return True

# API initialization functions
def initialize_gemini_api():
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return False, "Gemini API key not found"
        genai.configure(api_key=api_key)
        return True, "Gemini API initialized successfully"
    except Exception as e:
        return False, f"Error initializing Gemini API: {str(e)}"

def initialize_deepseek_api(api_key=None):
    try:
        if not api_key:
            api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return False, None, "OpenRouter API key not found"
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        return True, client, "DeepSeek API initialized successfully"
    except Exception as e:
        return False, None, f"Error initializing DeepSeek API: {str(e)}"

# AI processing functions
def customize_resume_gemini(resume_template, job_description, prompt):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            f"{prompt}\n\nJob Description:\n{job_description}\n\nResume Template:\n{resume_template}"
        )
        return True, response.text, "Resume customized successfully using Gemini"
    except Exception as e:
        return False, None, f"Error customizing resume with Gemini: {str(e)}"

def generate_cover_letter_gemini(resume, job_description, prompt, template):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            f"{prompt}\n\nJob Description:\n{job_description}\n\nResume:\n{resume}\n\nCover Letter Template:\n{template}"
        )
        return True, response.text, "Cover letter generated successfully using Gemini"
    except Exception as e:
        return False, None, f"Error generating cover letter with Gemini: {str(e)}"

def customize_resume_deepseek(client, resume_template, job_description, prompt):
    try:
        full_prompt = f"{prompt}\n\nJob Description:\n{job_description}\n\nResume Template:\n{resume_template}"
        
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://resume-customizer.app", 
                "X-Title": "Resume Customizer App",
            },
            model="deepseek/deepseek-r1:free",
            messages=[
                {"role": "system", "content": "You are a professional resume writer."},
                {"role": "user", "content": full_prompt}
            ]
        )
        
        return True, response.choices[0].message.content, "Resume customized successfully using DeepSeek"
    except Exception as e:
        return False, None, f"Error customizing resume with DeepSeek: {str(e)}"

def generate_cover_letter_deepseek(client, resume, job_description, prompt, template):
    try:
        full_prompt = f"{prompt}\n\nJob Description:\n{job_description}\n\nResume:\n{resume}\n\nCover Letter Template:\n{template}"
        
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://resume-customizer.app",
                "X-Title": "Resume Customizer App",
            },
            model="deepseek/deepseek-r1:free",
            messages=[
                {"role": "system", "content": "You are a professional cover letter writer."},
                {"role": "user", "content": full_prompt}
            ]
        )
        
        return True, response.choices[0].message.content, "Cover letter generated successfully using DeepSeek"
    except Exception as e:
        return False, None, f"Error generating cover letter with DeepSeek: {str(e)}"

# Auto-save functions
def auto_save_resume_template(content):
    save_template("resume", content)
    return "Resume template auto-saved"

def auto_save_cover_letter_template(content):
    save_template("cover_letter", content)
    return "Cover letter template auto-saved"

def auto_save_prompts(resume_prompt_content, cover_letter_prompt_content):
    save_prompts(resume_prompt_content, cover_letter_prompt_content)
    return "Prompts auto-saved"

# Global state and initialization
resume_prompt, cover_letter_prompt = load_prompts()
gemini_available, gemini_status = initialize_gemini_api()
deepseek_available, deepseek_client, deepseek_status = initialize_deepseek_api()

# JavaScript for UI interactions
js_code = """
function toggleSettings() {
    const settings = document.querySelector('.hidden-settings');
    settings.classList.toggle('open');
}

function closeSettings() {
    const settings = document.querySelector('.hidden-settings');
    settings.classList.remove('open');
}

function selectModel(model) {
    document.querySelectorAll('.model-option').forEach(el => {
        el.classList.remove('selected');
    });
    document.querySelector(`#model-${model}`).classList.add('selected');
    
    // Update hidden radio button
    const radioBtn = document.querySelector(`input[name="model_choice"][value="${model}"]`);
    if (radioBtn) radioBtn.checked = true;
}

function toggleResultView(viewType) {
    if (viewType === 'resume') {
        document.querySelector('#resume-view').classList.remove('hidden');
        document.querySelector('#cover-letter-view').classList.add('hidden');
    } else {
        document.querySelector('#resume-view').classList.add('hidden');
        document.querySelector('#cover-letter-view').classList.remove('hidden');
    }
}
"""

# Callback functions for UI interactions
def toggle_view(view_type):
    if view_type == "resume":
        return gr.update(visible=True), gr.update(visible=False)
    else:
        return gr.update(visible=False), gr.update(visible=True)

def upload_resume_template(file):
    if file is None:
        return gr.update(value=load_template("resume")), "No file uploaded"
    
    content = file.decode("utf-8")
    save_template("resume", content)
    return gr.update(value=content), "Resume template uploaded and saved"

def upload_cover_letter_template(file):
    if file is None:
        return gr.update(value=load_template("cover_letter")), "No file uploaded"
    
    content = file.decode("utf-8")
    save_template("cover_letter", content)
    return gr.update(value=content), "Cover letter template uploaded and saved"

def save_openrouter_key(api_key):
    if not api_key:
        return "Please enter an API key", update_api_status()
    
    os.environ["OPENROUTER_API_KEY"] = api_key
    success, client, message = initialize_deepseek_api(api_key)
    
    if success:
        global deepseek_available, deepseek_client
        deepseek_available = True
        deepseek_client = client
        return "OpenRouter API key saved successfully", update_api_status()
    else:
        return f"Error: {message}", update_api_status()

def update_api_status():
    gemini_available, gemini_status = initialize_gemini_api()
    deepseek_available, deepseek_client, deepseek_status = initialize_deepseek_api()
    
    status_text = f"Gemini API: {'✓ Available' if gemini_available else '✗ Unavailable'}\n"
    status_text += f"DeepSeek API: {'✓ Available' if deepseek_available else '✗ Unavailable'}"
    
    return status_text

def generate_documents(job_description, model_choice, resume_template_text, cover_letter_template_text, resume_prompt_input, cover_letter_prompt_input):
    if not job_description:
        return "Please enter a job description", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update(), gr.update(visible=False)
    
    if not resume_template_text:
        return "Resume template is missing", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update(), gr.update(visible=False)
    
    if not cover_letter_template_text:
        return "Cover letter template is missing", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update(), gr.update(visible=False)
    
    # Customize resume
    if model_choice == "Gemini" and gemini_available:
        success, customized_resume, message = customize_resume_gemini(resume_template_text, job_description, resume_prompt_input)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, customized_resume, message = customize_resume_deepseek(deepseek_client, resume_template_text, job_description, resume_prompt_input)
    else:
        return f"{model_choice} API is not available", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update(), gr.update(visible=False)
    
    if not success:
        return f"Error: {message}", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update(), gr.update(visible=False)
    
    # Generate cover letter
    if model_choice == "Gemini" and gemini_available:
        success, cover_letter, message = generate_cover_letter_gemini(customized_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, cover_letter, message = generate_cover_letter_deepseek(deepseek_client, customized_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    else:
        return f"{model_choice} API is not available", gr.update(visible=True), gr.update(visible=False), customized_resume, gr.update(), gr.update(visible=True)
    
    if not success:
        return f"Resume customized, but error generating cover letter: {message}", gr.update(visible=True), gr.update(visible=False), customized_resume, gr.update(), gr.update(visible=True)
    
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_text = f"Documents generated successfully with {model_choice}"
    
    # Save files for download
    resume_file = f"customized_resume_{int(time.time())}.tex"
    with open(resume_file, "w") as f:
        f.write(customized_resume)
    
    cover_letter_file = f"cover_letter_{int(time.time())}.tex"
    with open(cover_letter_file, "w") as f:
        f.write(cover_letter)
    
    return status_text, gr.update(visible=True), gr.update(visible=True), customized_resume, cover_letter, gr.update(visible=True)

def regenerate_resume(job_description, model_choice, resume_template_text, resume_prompt_input, cover_letter_output):
    if model_choice == "Gemini" and gemini_available:
        success, customized_resume, message = customize_resume_gemini(resume_template_text, job_description, resume_prompt_input)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, customized_resume, message = customize_resume_deepseek(deepseek_client, resume_template_text, job_description, resume_prompt_input)
    else:
        return f"{model_choice} API is not available", gr.update(), gr.update()
    
    if not success:
        return f"Error: {message}", gr.update(), gr.update()
    
    # Save file for download
    resume_file = f"customized_resume_{int(time.time())}.tex"
    with open(resume_file, "w") as f:
        f.write(customized_resume)
    
    return f"Resume regenerated successfully using {model_choice}", customized_resume, cover_letter_output

def regenerate_cover_letter(job_description, model_choice, current_resume, cover_letter_template_text, cover_letter_prompt_input):
    if not current_resume:
        return "Please generate a resume first", gr.update(), gr.update()
    
    if model_choice == "Gemini" and gemini_available:
        success, cover_letter, message = generate_cover_letter_gemini(current_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, cover_letter, message = generate_cover_letter_deepseek(deepseek_client, current_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    else:
        return f"{model_choice} API is not available", gr.update(), gr.update()
    
    if not success:
        return f"Error: {message}", gr.update(), gr.update()
    
    # Save file for download
    cover_letter_file = f"cover_letter_{int(time.time())}.tex"
    with open(cover_letter_file, "w") as f:
        f.write(cover_letter)
    
    return f"Cover letter regenerated successfully using {model_choice}", current_resume, cover_letter

# Create Gradio interface with Perplexity-like UI
with gr.Blocks(css=custom_css, theme=gr.themes.Base()) as app:
    # JS for interactivity
    gr.HTML(f"<script>{js_code}</script>")
    
    # Hidden settings panel (initially closed)
    with gr.Column(elem_id="settings-panel", elem_classes=["hidden-settings"]):
        gr.HTML('<span class="close-settings" onclick="closeSettings()">×</span>')
        gr.Markdown("## Settings")
        
        with gr.Group(elem_classes=["settings-section"]):
            gr.Markdown("### API Status")
            api_status = gr.Markdown(update_api_status())
            
            # OpenRouter API Key input for DeepSeek
            with gr.Group(visible=not deepseek_available):
                openrouter_key = gr.Textbox(
                    label="OpenRouter API Key (for DeepSeek)",
                    placeholder="Enter your OpenRouter API key here",
                    type="password"
                )
                save_key_btn = gr.Button("Save API Key")
                api_key_status = gr.Markdown("")
                save_key_btn.click(
                    save_openrouter_key,
                    inputs=[openrouter_key],
                    outputs=[api_key_status, api_status]
                )
        
        with gr.Group(elem_classes=["settings-section"]):
            gr.Markdown("### Resume Template")
            resume_template_file = gr.File(
                label="Upload Resume LaTeX Template",
                file_types=[".tex"],
                type="binary"
            )
            resume_upload_status = gr.Markdown("")
            resume_template_text = gr.Textbox(
                label="Edit Resume Template",
                value=load_template("resume"),
                lines=10
            )
            # Auto-save for resume template
            resume_template_text.change(
                auto_save_resume_template,
                inputs=[resume_template_text],
                outputs=[resume_upload_status]
            )
        
        with gr.Group(elem_classes=["settings-section"]):
            gr.Markdown("### Cover Letter Template")
            cover_letter_template_file = gr.File(
                label="Upload Cover Letter LaTeX Template",
                file_types=[".tex"],
                type="binary"
            )
            cover_letter_upload_status = gr.Markdown("")
            cover_letter_template_text = gr.Textbox(
                label="Edit Cover Letter Template",
                value=load_template("cover_letter"),
                lines=10
            )
            # Auto-save for cover letter template
            cover_letter_template_text.change(
                auto_save_cover_letter_template,
                inputs=[cover_letter_template_text],
                outputs=[cover_letter_upload_status]
            )
        
        with gr.Group(elem_classes=["settings-section"]):
            gr.Markdown("### AI Prompts")
            resume_prompt_input = gr.Textbox(
                label="Resume Customization Prompt",
                value=resume_prompt,
                lines=6
            )
            cover_letter_prompt_input = gr.Textbox(
                label="Cover Letter Generation Prompt",
                value=cover_letter_prompt,
                lines=6
            )
            prompt_status = gr.Markdown("")
            # Auto-save for prompts
            resume_prompt_input.change(
                auto_save_prompts,
                inputs=[resume_prompt_input, cover_letter_prompt_input],
                outputs=[prompt_status]
            )
            cover_letter_prompt_input.change(
                auto_save_prompts,
                inputs=[resume_prompt_input, cover_letter_prompt_input],
                outputs=[prompt_status]
            )
    
    # Main header
    with gr.Row(elem_classes=["header"]):
        gr.Markdown("# AI Resume & Cover Letter Customizer")
        gr.HTML('<div class="settings-toggle" onclick="toggleSettings()"><span>⚙️</span><span>Settings</span></div>')
    
    # Result area (initially hidden)
    results_container = gr.Group(visible=False, elem_classes=["result-container"])
    
    with results_container:
        generation_status = gr.Markdown("Documents generated successfully")
        
        with gr.Row(elem_classes=["answer-header"]):
            gr.Markdown("### Generated Documents")
            
            with gr.Column():
                view_resume_btn = gr.Button("View Resume", elem_classes=["action-button"])
                view_cl_btn = gr.Button("View Cover Letter", elem_classes=["action-button"])
        
        # Resume view
        with gr.Group(elem_id="resume-view"):
            gr.Markdown("## Customized Resume")
            customized_resume_output = gr.Textbox(
                lines=15,
                label="",
                elem_classes=["tex-output"]
            )
            
            with gr.Row():
                regenerate_resume_btn = gr.Button("Regenerate", elem_classes=["action-button"])
                download_resume_btn = gr.Button("Download", elem_classes=["action-button", "primary"])
            
            with gr.Group(elem_classes=["source-list"]):
                gr.Markdown("### Sources")
                gr.Markdown("1. Resume Template", elem_classes=["source-item"])
                gr.Markdown("2. Job Description Analysis", elem_classes=["source-item"])
        
        # Cover letter view (initially hidden)
        with gr.Group(elem_id="cover-letter-view", visible=False):
            gr.Markdown("## Cover Letter")
            cover_letter_output = gr.Textbox(
                lines=15,
                label="",
                elem_classes=["tex-output"]
            )
            
            with gr.Row():
                regenerate_cl_btn = gr.Button("Regenerate", elem_classes=["action-button"])
                download_cl_btn = gr.Button("Download", elem_classes=["action-button", "primary"])
            
            with gr.Group(elem_classes=["source-list"]):
                gr.Markdown("### Sources")
                gr.Markdown("1. Cover Letter Template", elem_classes=["source-item"])
                gr.Markdown("2. Customized Resume", elem_classes=["source-item"])
                gr.Markdown("3. Job Description Analysis", elem_classes=["source-item"])
    
    # Central search area - Perplexity style
    with gr.Group(elem_classes=["central-search"]):
        gr.Markdown("## Customize your resume for any job")
        
        # Model selection in the central area
        with gr.Row(elem_classes=["model-select"]):
            gr.HTML(f'''
                <div id="model-Gemini" class="model-option {"selected" if gemini_available else ""}" 
                     onclick="selectModel('Gemini')" 
                     {"style='opacity:0.5;cursor:not-allowed'" if not gemini_available else ""}>
                    Gemini
                </div>
                <div id="model-DeepSeek" class="model-option {"selected" if not gemini_available and deepseek_available else ""}" 
                     onclick="selectModel('DeepSeek')"
                     {"style='opacity:0.5;cursor:not-allowed'" if not deepseek_available else ""}>
                    DeepSeek
                </div>
            ''')
            
            # Hidden radio button for actual model selection
            model_choice = gr.Radio(
                choices=["Gemini", "DeepSeek"],
                value="Gemini" if gemini_available else "DeepSeek" if deepseek_available else None,
                label="Model",
                visible=False
            )
        
        with gr.Row(elem_classes=["search-bar"]):
            job_description = gr.Textbox(
                placeholder="Paste your job description here...",
                lines=1,
                label=""
            )
            generate_btn = gr.Button("Generate", elem_classes=["action-button", "primary"])
        
        gr.Markdown("Or try one of these examples:", elem_classes=["related-questions"])
        
        with gr.Row(elem_classes=["related-questions"]):
            example1_btn = gr.Button("Data Scientist", elem_classes=["related-question"])
            example2_btn = gr.Button("Software Engineer", elem_classes=["related-question"])
            example3_btn = gr.Button("Marketing Manager", elem_classes=["related-question"])
    
    # Footer
    with gr.Row(elem_classes=["footer"]):
        gr.Markdown("AI Resume & Cover Letter Customizer • Created with Gradio • © 2025")
    
    # Setup event handlers
    resume_template_file.upload(
        upload_resume_template,
        inputs=[resume_template_file],
        outputs=[resume_template_text, resume_upload_status]
    )
    
    cover_letter_template_file.upload(
        upload_cover_letter_template,
        inputs=[cover_letter_template_file],
        outputs=[cover_letter_template_text, cover_letter_upload_status]
    )
    
    # View toggle buttons
    view_resume_btn.click(
        lambda: (gr.update(visible=True), gr.update(visible=False)),
        outputs=[gr.Group(elem_id="resume-view"), gr.Group(elem_id="cover-letter-view")]
    )
    
    view_cl_btn.click(
        lambda: (gr.update(visible=False), gr.update(visible=True)),
        outputs=[gr.Group(elem_id="resume-view"), gr.Group(elem_id="cover-letter-view")]
    )
    
    # Generation button
    generate_btn.click(
        generate_documents,
        inputs=[
            job_description,
            model_choice,
            resume_template_text,
            cover_letter_template_text,
            resume_prompt_input,
            cover_letter_prompt_input
        ],
        outputs=[
            generation_status,
            download_resume_btn,
            download_cl_btn,
            customized_resume_output,
            cover_letter_output,
            results_container
        ]
    )
    
    # Regenerate buttons
    regenerate_resume_btn.click(
        regenerate_resume,
        inputs=[
            job_description,
            model_choice,
            resume_template_text,
            resume_prompt_input,
            cover_letter_output
        ],
        outputs=[
            generation_status,
            customized_resume_output,
            cover_letter_output
        ]
    )
    
    regenerate_cl_btn.click(
        regenerate_cover_letter,
        inputs=[
            job_description,
            model_choice,
            customized_resume_output,
            cover_letter_template_text,
            cover_letter_prompt_input
        ],
        outputs=[
            generation_status,
            customized_resume_output,
            cover_letter_output
        ]
    )
    
    # Download buttons
    download_resume_btn.click(
        lambda: f"customized_resume_{int(time.time())}.tex",
        inputs=None,
        outputs=gr.File(label="Download")
    )
    
    download_cl_btn.click(
        lambda: f"cover_letter_{int(time.time())}.tex",
        inputs=None,
        outputs=gr.File(label="Download")
    )
    
    # Example buttons
    example1_btn.click(
        lambda: "Experience with data analysis, statistical modeling, and machine learning required. Proficiency in Python, R, SQL, and data visualization tools. PhD or Master's degree in Statistics, Computer Science, or related field preferred. 5+ years of experience working with large datasets and implementing machine learning models in production environments.",
        outputs=job_description
    )
    
    example2_btn.click(
        lambda: "Seeking a full-stack software engineer with 3+ years of experience in JavaScript, React, Node.js, and MongoDB. Knowledge of AWS cloud services required. Bachelor's degree in Computer Science or equivalent experience. Strong problem-solving skills and experience with agile development methodologies.",
        outputs=job_description
    )
    
    example3_btn.click(
        lambda: "Looking for a marketing manager with experience in digital marketing, social media strategy, and campaign analytics. Excellent communication skills and ability to manage multiple projects required. Bachelor's degree in Marketing or related field. 4+ years of experience in marketing roles, preferably in a B2B environment.",
        outputs=job_description
    )

# Launch the app
if __name__ == "__main__":
    app.launch()
