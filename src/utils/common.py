"""Common utility functions for BizBrain."""
import os
import pathlib

def load_anthropic_api_key():
    """Load Anthropic API key from config file into environment variable.
    Returns True if key is available (either already in env or loaded from file).
    Returns False if key is not available.
    """
    if "ANTHROPIC_API_KEY" not in os.environ:
        try:
            config_path = pathlib.Path(__file__).parent.parent.parent / "config_env.py"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    for line in f:
                        if "ANTHROPIC_API_KEY=" in line:
                            key = line.split("=", 1)[1].strip()
                            os.environ["ANTHROPIC_API_KEY"] = key
                            return True
        except Exception:
            pass
    return "ANTHROPIC_API_KEY" in os.environ