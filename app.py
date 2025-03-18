import os
import json
import gradio as gr
import google.generativeai as genai
from openai import OpenAI
import tempfile
import time
from pathlib import Path
from datetime import datetime

# Theme and styling with new color scheme
custom_css = """
body {
    background-color: #FFFFEE !important;
}
.gradio-container {
    background-color: #FFFFEE !important;
}
.gr-sidebar-item {
    background-color: #F8F8E2 !important;
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 10px;
}
.gr-form {
    background-color: #F8F8E2 !important;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
}
.container {
    max-width: 1200px;
    margin: auto;
}
.header {
    text-align: center;
    margin-bottom: 20px;
}
.status-success {
    color: #28a745;
    font-weight: bold;
}
.status-error {
    color: #dc3545;
    font-weight: bold;
}
.footer {
    text-align: center;
    margin-top: 30px;
    font-size: 0.8em;
    color: #6c757d;
}
.settings-item {
    background-color: #F8F8E2 !important;
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 10px;
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

# Global state and initialization
resume_prompt, cover_letter_prompt = load_prompts()
gemini_available, gemini_status = initialize_gemini_api()
deepseek_available, deepseek_client, deepseek_status = initialize_deepseek_api()

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

# Callback functions
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

def update_api_status():
    gemini_available, gemini_status = initialize_gemini_api()
    deepseek_available, deepseek_client, deepseek_status = initialize_deepseek_api()
    
    status_text = f"Gemini API: {'✓ Available' if gemini_available else '✗ Unavailable'}\n"
    status_text += f"DeepSeek API: {'✓ Available' if deepseek_available else '✗ Unavailable'}"
    
    return status_text

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

def generate_documents(job_description, model_choice, resume_template_text, cover_letter_template_text, resume_prompt_input, cover_letter_prompt_input):
    if not job_description:
        return "Please enter a job description", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update()
    
    if not resume_template_text:
        return "Resume template is missing", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update()
    
    if not cover_letter_template_text:
        return "Cover letter template is missing", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update()
    
    # Initialize status
    status_text = f"Generating documents using {model_choice}..."
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Customize resume
    if model_choice == "Gemini" and gemini_available:
        success, customized_resume, message = customize_resume_gemini(resume_template_text, job_description, resume_prompt_input)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, customized_resume, message = customize_resume_deepseek(deepseek_client, resume_template_text, job_description, resume_prompt_input)
    else:
        return f"{model_choice} API is not available", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update()
    
    if not success:
        return f"Error: {message}", gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update()
    
    # Generate cover letter
    if model_choice == "Gemini" and gemini_available:
        success, cover_letter, message = generate_cover_letter_gemini(customized_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, cover_letter, message = generate_cover_letter_deepseek(deepseek_client, customized_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    else:
        return f"{model_choice} API is not available", gr.update(visible=True), gr.update(visible=False), customized_resume, gr.update()
    
    if not success:
        return f"Resume customized, but error generating cover letter: {message}", gr.update(visible=True), gr.update(visible=False), customized_resume, gr.update()
    
    status_text = f"✓ Resume and Cover Letter generated successfully with {model_choice} at {generation_time}"
    
    # Save files temporarily for download
    resume_file = f"customized_resume_{int(time.time())}.tex"
    with open(resume_file, "w") as f:
        f.write(customized_resume)
    
    cover_letter_file = f"cover_letter_{int(time.time())}.tex"
    with open(cover_letter_file, "w") as f:
        f.write(cover_letter)
    
    return status_text, gr.update(visible=True), gr.update(visible=True), customized_resume, cover_letter

def regenerate_resume(job_description, model_choice, resume_template_text, resume_prompt_input, cover_letter_output):
    if not job_description:
        return "Please enter a job description", gr.update(), gr.update()
    
    if model_choice == "Gemini" and gemini_available:
        success, customized_resume, message = customize_resume_gemini(resume_template_text, job_description, resume_prompt_input)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, customized_resume, message = customize_resume_deepseek(deepseek_client, resume_template_text, job_description, resume_prompt_input)
    else:
        return f"{model_choice} API is not available", gr.update(), gr.update()
    
    if not success:
        return f"Error: {message}", gr.update(), gr.update()
    
    # Save file temporarily for download
    resume_file = f"customized_resume_{int(time.time())}.tex"
    with open(resume_file, "w") as f:
        f.write(customized_resume)
    
    return f"Resume regenerated successfully using {model_choice}", customized_resume, cover_letter_output

def regenerate_cover_letter(job_description, model_choice, current_resume, cover_letter_template_text, cover_letter_prompt_input):
    if not job_description or not current_resume:
        return "Please generate a resume first", gr.update(), gr.update()
    
    if model_choice == "Gemini" and gemini_available:
        success, cover_letter, message = generate_cover_letter_gemini(current_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, cover_letter, message = generate_cover_letter_deepseek(deepseek_client, current_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    else:
        return f"{model_choice} API is not available", gr.update(), gr.update()
    
    if not success:
        return f"Error: {message}", gr.update(), gr.update()
    
    # Save file temporarily for download
    cover_letter_file = f"cover_letter_{int(time.time())}.tex"
    with open(cover_letter_file, "w") as f:
        f.write(cover_letter)
    
    return f"Cover letter regenerated successfully using {model_choice}", current_resume, cover_letter

# Create Gradio interface with the new UI layout
with gr.Blocks(css=custom_css, theme=gr.themes.Base()) as app:
    # Page header
    with gr.Row():
        gr.Markdown("# AI Resume & Cover Letter Customizer", elem_classes=["header"])
    
    # Main layout with sidebar and content area
    with gr.Row():
        # Left sidebar for settings
        with gr.Column(scale=1):
            gr.Markdown("## Settings")
            
            with gr.Accordion("AI Model", open=True, elem_classes=["settings-item"]):
                api_status = gr.Markdown(update_api_status())
                model_choice = gr.Radio(
                    label="Select AI Model",
                    choices=["Gemini", "DeepSeek"],
                    value="Gemini" if gemini_available else "DeepSeek" if deepseek_available else None,
                    interactive=True
                )
                
                with gr.Group(visible=not deepseek_available, elem_classes=["settings-item"]):
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
            
            with gr.Accordion("Resume Template", open=True, elem_classes=["settings-item"]):
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
                # Set up auto-save for resume template
                resume_template_text.change(
                    auto_save_resume_template,
                    inputs=[resume_template_text],
                    outputs=[resume_upload_status]
                )
            
            with gr.Accordion("Cover Letter Template", open=True, elem_classes=["settings-item"]):
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
                # Set up auto-save for cover letter template
                cover_letter_template_text.change(
                    auto_save_cover_letter_template,
                    inputs=[cover_letter_template_text],
                    outputs=[cover_letter_upload_status]
                )
            
            with gr.Accordion("AI Prompts", open=False, elem_classes=["settings-item"]):
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
                # Set up auto-save for prompts
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
        
        # Right main content area
        with gr.Column(scale=2):
            # Results section at the top
            generation_status = gr.Markdown("Enter a job description below and click Generate")
            
            with gr.Tabs() as result_tabs:
                with gr.TabItem("Customized Resume"):
                    customized_resume_output = gr.Textbox(
                        label="Customized Resume (LaTeX)",
                        lines=18,
                        interactive=True
                    )
                    with gr.Row():
                        regenerate_resume_btn = gr.Button("Regenerate Resume")
                        download_resume_btn = gr.Button("Download Resume", visible=False)
                
                with gr.TabItem("Cover Letter"):
                    cover_letter_output = gr.Textbox(
                        label="Cover Letter (LaTeX)",
                        lines=18,
                        interactive=True
                    )
                    with gr.Row():
                        regenerate_cl_btn = gr.Button("Regenerate Cover Letter")
                        download_cl_btn = gr.Button("Download Cover Letter", visible=False)
            
            # Input section at the bottom
            with gr.Group():
                gr.Markdown("## Job Description")
                job_description = gr.Textbox(
                    placeholder="Paste the job description here...",
                    lines=10,
                    label="Job Description Input"
                )
                generate_btn = gr.Button("Generate Customized Documents", variant="primary", size="lg")
    
    # Footer
    with gr.Row():
        gr.Markdown("AI Resume & Cover Letter Customizer • Created with Gradio • Version 2.0", elem_classes=["footer"])
    
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
            cover_letter_output
        ]
    )
    
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

# Launch the app
if __name__ == "__main__":
    app.launch()
