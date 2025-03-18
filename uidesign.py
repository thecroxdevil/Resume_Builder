import gradio as gr

# Custom CSS for minimalist design
custom_css = """
body {
    font-family: 'Helvetica Neue', sans-serif;
    color: #333;
}
.container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px;
}
.header-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 20px;
    border-bottom: 1px solid #eee;
    margin-bottom: 30px;
}
.nav-links {
    display: flex;
    gap: 20px;
}
.nav-links a {
    text-decoration: none;
    color: #555;
    font-weight: 500;
}
.nav-links a:hover {
    color: #007bff;
}
.profile-icon {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background-color: #ddd; /* Placeholder for user icon */
}
.search-section {
    text-align: center;
    margin-bottom: 40px;
}
.search-bar-container {
    display: flex;
    justify-content: center;
    margin-bottom: 10px;
}
.search-bar {
    padding: 12px 15px;
    border: 1px solid #ccc;
    border-radius: 5px 0 0 5px;
    width: 60%;
    max-width: 700px;
    font-size: 1rem;
}
.ask-button {
    padding: 12px 25px;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 0 5px 5px 0;
    cursor: pointer;
    font-size: 1rem;
}
.ask-button:hover {
    background-color: #0056b3;
}
.example-queries {
    color: #777;
    font-size: 0.9rem;
}
.example-queries p {
    margin-bottom: 5px;
}
.example-queries span {
    cursor: pointer;
    text-decoration: underline dotted;
}
.example-queries span:hover {
    color: #007bff;
}
.results-section {
    padding: 20px;
    background-color: #f8f9fa;
    border-radius: 8px;
    margin-top: 20px;
}
.query-display {
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 15px;
}
.ai-answer {
    line-height: 1.6;
    margin-bottom: 20px;
}
.citation {
    font-size: 0.8rem;
    vertical-align: super;
    color: #007bff;
    text-decoration: none;
}
.sources-section {
    margin-top: 20px;
    border-top: 1px solid #eee;
    padding-top: 15px;
}
.sources-list {
    list-style: none;
    padding-left: 0;
}
.sources-list li {
    margin-bottom: 8px;
}
.sources-list a {
    text-decoration: none;
    color: #007bff;
}
.related-questions-section {
    margin-top: 25px;
    border-top: 1px solid #eee;
    padding-top: 15px;
}
.related-questions-list {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    list-style: none;
    padding-left: 0;
}
.related-questions-list li {
    margin-bottom: 8px;
}
.related-questions-list button {
    background-color: #e9ecef;
    border: none;
    padding: 8px 12px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 0.9rem;
    color: #555;
}
.related-questions-list button:hover {
    background-color: #dee2e6;
}
.follow-up-input-section {
    margin-top: 30px;
    border-top: 1px solid #eee;
    padding-top: 20px;
}
.follow-up-input {
    width: 100%;
    padding: 12px 15px;
    border: 1px solid #ccc;
    border-radius: 5px;
    font-size: 1rem;
}
"""

def search_interface(query):
    if not query:
        return "Please enter a query."

    ai_answer_content = """
    The Eiffel Tower, completed in 1889, is a wrought-iron lattice tower on the Champ de Mars in Paris, France [1]. It was named after the engineer Gustave Eiffel, whose company designed and built the tower. Initially criticized by some of France's leading artists and intellectuals for its design, the Eiffel Tower has become a global cultural icon of France and one of the most recognizable structures in the world [2]. It is the most-visited paid monument in the world; millions of people ascend it every year.
    """

    sources_content = """
    1. <a href="https://www.example.com/eiffel1" target="_blank">Example Source 1 - Eiffel Tower History</a>
    2. <a href="https://www.example.com/eiffel2" target="_blank">Example Source 2 - Eiffel Tower Design and Criticism</a>
    """

    related_questions = [
        "Who designed the Eiffel Tower?",
        "When was the Eiffel Tower built?",
        "Why was the Eiffel Tower controversial?",
        "What is the height of the Eiffel Tower?"
    ]

    ai_answer_formatted = ai_answer_content.replace("[1]", "<sup class='citation'>[1]</sup>").replace("[2]", "<sup class='citation'>[2]</sup>")

    sources_list_html = "<ul class='sources-list'>"
    for i, source in enumerate(sources_content.strip().split('\n')):
        sources_list_html += f"<li>{i+1}. {source}</li>"
    sources_list_html += "</ul>"

    related_questions_buttons = ""
    related_questions_list_html = "<ul class='related-questions-list'>"
    for question in related_questions:
        related_questions_list_html += f"<li><button onclick='(function(){{document.getElementById(\"search-input\").value = \"{question}\";}})()'>{question}</button></li>" # Inline JS for example, better to handle with Gradio events in real app
    related_questions_list_html += "</ul>"


    results_html = f"""
        <div class='results-section'>
            <div class='query-display'>Your query: "{query}"</div>
            <div class='ai-answer'>{ai_answer_formatted}</div>
            <div class='sources-section'>
                <h3>Sources</h3>
                {sources_list_html}
            </div>
            <div class='related-questions-section'>
                <h3>Explore Further</h3>
                {related_questions_list_html}
            </div>
        </div>
    """

    return results_html

with gr.Blocks(css=custom_css) as demo:
    gr.HTML("<div class='container'>")

    with gr.Row(elem_classes="header-nav"):
        with gr.Column():
            gr.HTML("<h1>Search AI</h1>")
        with gr.Column(align="right"):
            with gr.Row(elem_classes="nav-links"):
                gr.HTML("<a href='#'>Search</a>")
                gr.HTML("<a href='#'>Discover</a>")
                gr.HTML("<a href='#'>Library</a>")
                gr.HTML("<div class='profile-icon'></div>") # Placeholder icon

    with gr.Column(elem_classes="search-section"):
        gr.HTML("<p>Ask anything. Get concise answers with sources.</p>")
        with gr.Row(elem_classes="search-bar-container"):
            search_input = gr.Textbox(
                placeholder="Ask me anything...",
                elem_classes="search-bar",
                show_label=False,
                lines=1,
                container=False,
                elem_id="search-input" # For JS interaction example
            )
            ask_button = gr.Button("Ask", elem_classes="ask-button")
        with gr.Column(elem_classes="example-queries"):
            gr.HTML("<p>Example queries: <span onclick='(function(){{document.getElementById(\"search-input\").value = \"What is the capital of France?\";}})()'>What is the capital of France?</span> | <span onclick='(function(){{document.getElementById(\"search-input\").value = \"Explain quantum physics simply.\";}})()'>Explain quantum physics simply.</span> | <span onclick='(function(){{document.getElementById(\"search-input\").value = \"Benefits of meditation.\";}})()'>Benefits of meditation.</span></p>")

    results_output = gr.HTML("")

    follow_up_input = gr.Textbox(placeholder="Ask a follow-up question...", elem_classes="follow-up-input", show_label=False, container=False)

    gr.HTML("</div>") # Close container div

    ask_button.click(search_interface, inputs=search_input, outputs=results_output)
    follow_up_input.submit(search_interface, inputs=follow_up_input, outputs=results_output) # Example for follow-up


demo.launch()
