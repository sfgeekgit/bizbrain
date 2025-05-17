#!/usr/bin/env python3
"""
BizBrain Web Interface

Web-based interface for the BizBrain Q&A system with authentication and a clean UI.
Provides access to core functionality including document status viewing and Q&A.
"""

import os
import sys
import json
import gradio as gr
import pathlib

# Add the project root to the Python path
root_dir = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from interface.cli import BizBrainCLI
from utils.dir_setup import ensure_directories

# CSS rules to clean up the Gradio interface
# Hides footer, settings toggle, logo, and some Svelte components for a cleaner UI
GRADIO_CSS = """
    footer {display: none !important;}
    #settings-toggle {display: none !important;}
    #logo {display: none !important;}
    .svelte-1ipelgc {display: none !important;}
"""

def load_auth_credentials():
    '''
    THIS IS A QUICK AND DIRTY AUTH to get an MVP functional.
    For our use case it's almost certainly "Good enough" but this would not pass a security audit.
    see notes in auth_config.py for suggestions
    '''

    auth_config_path = root_dir / "auth_config.py"
    if not auth_config_path.exists():
        return None, None
    username, password = None, None

    try:
        with open(auth_config_path, 'r') as f:
            for line in f:
                if line.startswith("WEB_USERNAME"):
                    username = line.split("=", 1)[1].strip().strip('"\'')
                elif line.startswith("WEB_PASSWORD"):
                    password = line.split("=", 1)[1].strip().strip('"\'')
    except Exception:
        return None, None
    return username, password

def format_document_status(status_data):
    """Format document status data as HTML for display in the web UI."""
    if not status_data:
        return "No documents have been processed yet."
    
    html = ""
    
    # Format registry info
    html += f"<h3>System Information</h3>"
    html += f"<p>Total Documents: {status_data['registry_info']['total_documents']}<br>"
    html += f"Total Chunks: {status_data['registry_info']['total_chunks']}<br>"
    html += f"Total Batches: {status_data['registry_info']['total_batches']}<br>"
    html += f"Last Update: {status_data['registry_info']['last_update']}</p>"
    
    # Format batches table
    if status_data['batches']:
        html += f"<h3>Batches</h3>"
        html += "<table width='100%'>"
        html += "<tr><th>Batch ID</th><th>Effective Date</th><th>Created At</th><th>Document Count</th></tr>"
        
        for batch in status_data['batches']:
            html += "<tr>"
            html += f"<td>{batch['batch_id']}</td>"
            html += f"<td>{batch['effective_date']}</td>"
            html += f"<td>{batch['created_at']}</td>"
            html += f"<td>{batch['document_count']}</td>"
            html += "</tr>"
        
        html += "</table>"
    
    # Format documents table
    if status_data['documents']:
        html += f"<h3>Documents</h3>"
        html += "<table width='100%'>"
        html += "<tr><th>Document ID</th><th>Status</th><th>Batch ID</th><th>Effective Date</th><th>Chunks</th><th>Filename</th></tr>"
        
        for doc in status_data['documents']:
            html += "<tr>"
            html += f"<td>{doc['document_id']}</td>"
            html += f"<td>{doc['status']}</td>"
            html += f"<td>{doc['batch_id']}</td>"
            html += f"<td>{doc['effective_date']}</td>"
            html += f"<td>{doc['chunk_count']}</td>"
            html += f"<td>{doc['filename']}</td>"
            html += "</tr>"
        
        html += "</table>"
    
    return html

def format_sources(sources):
    """Format sources as HTML for display in the web UI."""
    if not sources:
        return ""
    
    html = "<h3>Sources</h3><ul>"
    
    if isinstance(sources, str):
        html += f"<li>{sources}</li>"
    else:
        for source in sources:
            html += f"<li>{source}</li>"
    
    html += "</ul>"
    return html

def main():
    # Initialize authentication
    username, password = load_auth_credentials()

    if not username or not password:
        print("Auth Config not found. Bail out!") 
        quit()
    
    # Ensure directories exist
    ensure_directories()
    
    # Initialize BizBrainCLI
    bizbrain = BizBrainCLI()
    
    # Define handler functions for the web interface
    def ask_question(question):
        """Process a question and return the answer and sources."""
        if not question.strip():
            return "Please enter a question.", ""
        
        response = bizbrain.answer_question(question)
        sources_html = format_sources(response.get('sources', []))
        
        return response.get('answer', "No answer found."), sources_html
    
    def get_status():
        """Get and format document status."""
        status_data = bizbrain.get_document_status()
        return format_document_status(status_data)
    
    # Create the web interface
    with gr.Blocks(title="BizBrain Legal Document Q&A", css=GRADIO_CSS) as interface:
        gr.Markdown("## BizBrain Legal Document Q&A")
        
        with gr.Tabs():
            # Q&A Tab
            with gr.TabItem("Ask Question"):
                with gr.Row():
                    question_input = gr.Textbox(
                        label="Your Question",
                        placeholder="Enter a question about the documents...",
                        lines=3
                    )
                
                question_button = gr.Button("Submit Question", variant="primary")
                
                answer_output = gr.Textbox(label="Answer", lines=5)
                sources_output = gr.HTML(label="Sources")
                
                question_button.click(
                    ask_question,
                    inputs=question_input,
                    outputs=[answer_output, sources_output]
                )
            
            # Document Status Tab
            with gr.TabItem("Document Status"):
                status_button = gr.Button("Show Document Status", variant="primary")
                status_output = gr.HTML(label="Document Status")
                
                status_button.click(
                    get_status,
                    inputs=None,
                    outputs=status_output
                )
    
    # Launch the interface
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        auth=[(username, password)],
        show_api=False,
        pwa=False,
        share=False
    )
    
if __name__ == "__main__":
    main()