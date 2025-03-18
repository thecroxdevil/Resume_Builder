import os
import json
import gradio as gr
import google.generativeai as genai
from openai import OpenAI
import tempfile
import time
from pathlib import Path
from datetime import datetime
import base64

# Theme and styling
custom_css = """
.container {
    max-width: 1200px;
    margin: auto;
}
.header {
    text-align: center;
    margin-bottom: 20px;
}
.result-container {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    background-color: #f9f9f9;
    margin-top: 10px;
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
.template-box {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 10px;
    background-color: #f5f5f5;
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

# Callback functions
def upload_resume_template(file):
    if file is None:
        return "No file uploaded", load_template("resume"), gr.update(visible=False)
    
    content = file.decode("utf-8")
    save_template("resume", content)
    return "Resume template uploaded and saved", content, gr.update(visible=True)

def upload_cover_letter_template(file):
    if file is None:
        return "No file uploaded", load_template("cover_letter"), gr.update(visible=False)
    
    content = file.decode("utf-8")
    save_template("cover_letter", content)
    return "Cover letter template uploaded and saved", content, gr.update(visible=True)

def save_prompt_settings(resume_prompt_input, cover_letter_prompt_input):
    save_prompts(resume_prompt_input, cover_letter_prompt_input)
    return "Prompts saved successfully"

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
        return "Please enter a job description", "", "", "", gr.update(visible=False), gr.update(visible=False)
    
    if not resume_template_text:
        return "Resume template is missing", "", "", "", gr.update(visible=False), gr.update(visible=False)
    
    if not cover_letter_template_text:
        return "Cover letter template is missing", "", "", "", gr.update(visible=False), gr.update(visible=False)
    
    # Initialize status
    status_text = f"Generating documents using {model_choice}...\n"
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Customize resume
    if model_choice == "Gemini" and gemini_available:
        success, customized_resume, message = customize_resume_gemini(resume_template_text, job_description, resume_prompt_input)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, customized_resume, message = customize_resume_deepseek(deepseek_client, resume_template_text, job_description, resume_prompt_input)
    else:
        return f"{model_choice} API is not available", "", "", "", gr.update(visible=False), gr.update(visible=False)
    
    if not success:
        return f"Error: {message}", "", "", "", gr.update(visible=False), gr.update(visible=False)
    
    status_text += f"✓ Resume customized successfully\n"
    
    # Generate cover letter
    if model_choice == "Gemini" and gemini_available:
        success, cover_letter, message = generate_cover_letter_gemini(customized_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, cover_letter, message = generate_cover_letter_deepseek(deepseek_client, customized_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    else:
        return f"{model_choice} API is not available", customized_resume, "", generation_time, gr.update(visible=True), gr.update(visible=False)
    
    if not success:
        return f"Resume customized, but error generating cover letter: {message}", customized_resume, "", generation_time, gr.update(visible=True), gr.update(visible=False)
    
    status_text += f"✓ Cover letter generated successfully\n"
    status_text += f"Documents ready for download"
    
    # Save files temporarily for download
    resume_file = f"customized_resume_{int(time.time())}.tex"
    with open(resume_file, "w") as f:
        f.write(customized_resume)
    
    cover_letter_file = f"cover_letter_{int(time.time())}.tex"
    with open(cover_letter_file, "w") as f:
        f.write(cover_letter)
    
    return status_text, customized_resume, cover_letter, generation_time, gr.update(visible=True), gr.update(visible=True)

def regenerate_resume(job_description, model_choice, resume_template_text, resume_prompt_input, current_cover_letter, generation_time, dl_resume_visible, dl_cl_visible):
    if model_choice == "Gemini" and gemini_available:
        success, customized_resume, message = customize_resume_gemini(resume_template_text, job_description, resume_prompt_input)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, customized_resume, message = customize_resume_deepseek(deepseek_client, resume_template_text, job_description, resume_prompt_input)
    else:
        return f"{model_choice} API is not available", gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    
    if not success:
        return f"Error: {message}", gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    
    # Save file temporarily for download
    resume_file = f"customized_resume_{int(time.time())}.tex"
    with open(resume_file, "w") as f:
        f.write(customized_resume)
    
    return f"Resume regenerated successfully using {model_choice}", customized_resume, current_cover_letter, generation_time, dl_resume_visible, dl_cl_visible

def regenerate_cover_letter(job_description, model_choice, current_resume, resume_template_text, cover_letter_template_text, cover_letter_prompt_input, generation_time, dl_resume_visible, dl_cl_visible):
    if model_choice == "Gemini" and gemini_available:
        success, cover_letter, message = generate_cover_letter_gemini(current_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    elif model_choice == "DeepSeek" and deepseek_available:
        success, cover_letter, message = generate_cover_letter_deepseek(deepseek_client, current_resume, job_description, cover_letter_prompt_input, cover_letter_template_text)
    else:
        return f"{model_choice} API is not available", gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    
    if not success:
        return f"Error: {message}", gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    
    # Save file temporarily for download
    cover_letter_file = f"cover_letter_{int(time.time())}.tex"
    with open(cover_letter_file, "w") as f:
        f.write(cover_letter)
    
    return f"Cover letter regenerated successfully using {model_choice}", current_resume, cover_letter, generation_time, dl_resume_visible, dl_cl_visible

# Create Gradio interface
with gr.Blocks(css=custom_css, theme=gr.themes.Soft()) as app:
    # Page header
    with gr.Row(elem_classes=["header"]):
        gr.Markdown("# AI Resume & Cover Letter Customizer")
        gr.Markdown("Transform your resume and generate customized cover letters using AI")
    
    # Main layout
    with gr.Row():
        # Left sidebar for templates and settings
        with gr.Column(scale=1):
            with gr.Accordion("AI Model Selection", open=True):
                api_status = gr.Markdown(update_api_status())
                model_choice = gr.Radio(
                    label="Select AI Model",
                    choices=["Gemini", "DeepSeek"],
                    value="Gemini" if gemini_available else "DeepSeek" if deepseek_available else None,
                    interactive=True
                )
                
                with gr.Accordion("OpenRouter API Settings (for DeepSeek)", open=not deepseek_available):
                    openrouter_key = gr.Textbox(
                        label="OpenRouter API Key",
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
            
            with gr.Accordion("Resume Template", open=True):
                resume_template_file = gr.File(
                    label="Upload Resume LaTeX Template",
                    file_types=[".tex"],
                    type="binary"
                )
                resume_upload_status = gr.Markdown("No template uploaded yet")
                resume_template_text = gr.Textbox(
                    label="Resume Template",
                    value=load_template("resume"),
                    lines=10
                )
                resume_template_save = gr.Button("Save Edited Template")
                resume_template_save.click(
                    lambda x: (save_template("resume", x), "Template saved"),
                    inputs=[resume_template_text],
                    outputs=[resume_upload_status]
                )
            
            with gr.Accordion("Cover Letter Template", open=True):
                cover_letter_template_file = gr.File(
                    label="Upload Cover Letter LaTeX Template",
                    file_types=[".tex"],
                    type="binary"
                )
                cover_letter_upload_status = gr.Markdown("No template uploaded yet")
                cover_letter_template_text = gr.Textbox(
                    label="Cover Letter Template",
                    value=load_template("cover_letter"),
                    lines=10
                )
                cover_letter_template_save = gr.Button("Save Edited Template")
                cover_letter_template_save.click(
                    lambda x: (save_template("cover_letter", x), "Template saved"),
                    inputs=[cover_letter_template_text],
                    outputs=[cover_letter_upload_status]
                )
            
            with gr.Accordion("AI Prompt Settings", open=False):
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
                prompt_save_btn = gr.Button("Save Prompts")
                prompt_status = gr.Markdown("")
                prompt_save_btn.click(
                    save_prompt_settings,
                    inputs=[resume_prompt_input, cover_letter_prompt_input],
                    outputs=[prompt_status]
                )
        
        # Right main area for input and results
        with gr.Column(scale=2):
            with gr.Column():
                gr.Markdown("## Job Description Input")
                job_description = gr.Textbox(
                    label="Paste the job description here",
                    placeholder="Enter the full job description...",
                    lines=10
                )
                generate_btn = gr.Button("Generate Customized Documents", variant="primary")
            
            # Results section
            with gr.Column():
                generation_status = gr.Markdown("Enter a job description and click Generate to start")
                generation_time = gr.Markdown(visible=False)
                
                with gr.Tabs():
                    with gr.TabItem("Customized Resume"):
                        customized_resume_output = gr.Textbox(
                            label="Customized Resume (LaTeX)",
                            lines=20
                        )
                        with gr.Row():
                            regenerate_resume_btn = gr.Button("Regenerate Resume")
                            download_resume_btn = gr.Button("Download Resume LaTeX", visible=False)
                    
                    with gr.TabItem("Cover Letter"):
                        cover_letter_output = gr.Textbox(
                            label="Cover Letter (LaTeX)",
                            lines=20
                        )
                        with gr.Row():
                            regenerate_cl_btn = gr.Button("Regenerate Cover Letter")
                            download_cl_btn = gr.Button("Download Cover Letter LaTeX", visible=False)
    
    # Footer
    with gr.Row(elem_classes=["footer"]):
        gr.Markdown("AI Resume & Cover Letter Customizer • Created with Gradio • Version 2.0")
    
    # Setup event handlers
    resume_template_file.upload(
        upload_resume_template,
        inputs=[resume_template_file],
        outputs=[resume_upload_status, resume_template_text, resume_template_save]
    )
    
    cover_letter_template_file.upload(
        upload_cover_letter_template,
        inputs=[cover_letter_template_file],
        outputs=[cover_letter_upload_status, cover_letter_template_text, cover_letter_template_save]
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
            customized_resume_output,
            cover_letter_output,
            generation_time,
            download_resume_btn,
            download_cl_btn
        ]
    )
    
    regenerate_resume_btn.click(
        regenerate_resume,
        inputs=[
            job_description,
            model_choice,
            resume_template_text,
            resume_prompt_input,
            cover_letter_output,
            generation_time,
            download_resume_btn,
            download_cl_btn
        ],
        outputs=[
            generation_status,
            customized_resume_output,
            cover_letter_output,
            generation_time,
            download_resume_btn,
            download_cl_btn
        ]
    )
    
    regenerate_cl_btn.click(
        regenerate_cover_letter,
        inputs=[
            job_description,
            model_choice,
            customized_resume_output,
            resume_template_text,
            cover_letter_template_text,
            cover_letter_prompt_input,
            generation_time,
            download_resume_btn,
            download_cl_btn
        ],
        outputs=[
            generation_status,
            customized_resume_output,
            cover_letter_output,
            generation_time,
            download_resume_btn,
            download_cl_btn
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
