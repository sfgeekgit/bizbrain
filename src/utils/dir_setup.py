import os

def ensure_directories():
    """Create all required directories if they don't exist."""
    directories = [
        "raw_documents",
        "processed_documents/full_text",
        "processed_documents/chunks",
        "vector_store",
        "conversation_history",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
