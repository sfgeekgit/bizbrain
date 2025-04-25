"""
Configuration settings for BizBrain application.
"""

# data such as keys should be stored in the project level root level directory  ../../config_env.py

# LLM Model settings
LLM_PROVIDER = "anthropic"  # Options: "anthropic", "openai", etc.
LLM_MODEL = "claude-3-7-sonnet-20250219"  # Default model to use
LLM_TEMPERATURE = 0.1  # Default temperature for LLM responses

# Embedding model settings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Default embedding model
EMBEDDING_DIMENSION = 384  # Dimension of the embedding model output

# Chunking settings
CHUNK_SIZE = 1000  # Default size for document chunks
CHUNK_OVERLAP = 200  # Default overlap between chunks

# Retrieval settings
DEFAULT_RETRIEVAL_TOP_K = 5  # Default number of chunks to retrieve
