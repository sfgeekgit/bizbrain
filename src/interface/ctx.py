#!/usr/bin/env python3
"""
BizBrain Web Interface Stub

A minimal web interface stub that demonstrates authentication with Gradio.
Future versions will integrate with the BizBrain Q&A system.
"""

import os
import sys
import gradio as gr
import pathlib

# Add the project root to the Python path
root_dir = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def load_auth_credentials():
    """Load authentication credentials from config file."""
    auth_config_path = root_dir / "auth_config.py"
    
    if not auth_config_path.exists():
        return None, None
        
    # Simple parsing of the auth_config.py file
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

def create_interface():
    """Create the Gradio interface."""
    username, password = load_auth_credentials()
    
    # Check if credentials were successfully loaded
    if not username or not password:
        # If credentials are missing, show an error interface
        def show_error():
            return "Authentication configuration not found. Please create auth_config.py in the project root."
            
        error_interface = gr.Interface(
            fn=show_error,
            inputs=None,
            outputs="text",
            title="BizBrain - Configuration Error",
            description="Error loading authentication configuration"
        )
        return error_interface
    
    # If credentials are available, create the main interface with authentication
    def greet(name):
        return f"Hello, {name}! Welcome to BizBrain."
    
    # Create the actual interface
    interface = gr.Interface(
        fn=greet,
        inputs="text",
        outputs="text",
        title="BizBrain Legal Document Q&A",
        description="Enter your name to get started",
        examples=[["User"]]
    )
    
    return interface

def main():
    """Main entry point for the web interface."""
    username, password = load_auth_credentials()
    interface = create_interface()

    # Launch with share=True to make it accessible beyond localhost
    # Use auth parameter in launch method for newer Gradio versions
    if username and password:
        interface.launch(share=True, 
        server_name="0.0.0.0", 
        server_port=7860,
        auth=[(username, password)])
    else:
        interface.launch(share=True)

if __name__ == "__main__":
    main()