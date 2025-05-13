#!/usr/bin/env python3
"""
BizBrain Web Interface Stub

Minimal Gradio interface with basic authentication and cleaned UI.
Future versions will integrate with the BizBrain Q&A system.
"""

import os
import sys
import gradio as gr
import pathlib

# Add the project root to the Python path
root_dir = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

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

def main():
    username, password = load_auth_credentials()

    if not username or not password:
        print("Auth Config not found. Bail out!") 
        quit()
        # This should check if the auth config exists at all, but I don't think it works as intended.
        # That's fine, just exit on launch for now. todo: better auth anyway
        '''
        def show_error():
            return "Authentication configuration not found. Please create auth_config.py in the project root."

        error_interface = gr.Interface(
            fn=show_error,
            inputs=None,
            outputs="text",
            title="BizBrain - Configuration Error",
            description="Error loading authentication configuration"
        )
        error_interface.launch()
        return
        '''
    
    def greet(name):
        return f"Hello, {name}! Welcome to BizBrain."

    with gr.Blocks(title="BizBrain Legal Document Q&A", css=GRADIO_CSS) as interface:
        gr.Markdown("### BizBrain Legal Document Q&A")
        with gr.Row():
            name = gr.Textbox(label="Your Name", placeholder="Enter your name")
            greet_button = gr.Button("Greet")
        output = gr.Textbox(label="Greeting")
        greet_button.click(greet, inputs=name, outputs=output)

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
