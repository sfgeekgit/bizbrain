#!/usr/bin/env python3
"""
BizBrain: A Python-based Q&A system for analyzing legal documents and contracts.
"""

import os
import argparse
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from utils.dir_setup import ensure_directories
from interface.cli import BizBrainCLI

def main():
    """Main entry point for BizBrain."""
    parser = argparse.ArgumentParser(description='BizBrain - Legal Document Q&A System')
    parser.add_argument('--batch-process', action='store_true', 
                        help='Process documents in batches with effective dates')
    parser.add_argument('--status', action='store_true', 
                        help='Show document status')
    parser.add_argument('--question', type=str, 
                        help='Ask a question')
    parser.add_argument('--interactive', action='store_true', 
                        help='Start interactive mode')
    # Keep the --process argument for backward compatibility but mark as deprecated
    parser.add_argument('--process', action='store_true',
                        help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_directories()
    
    # Create CLI interface
    bizbrain = BizBrainCLI()
    
    if args.batch_process:
        bizbrain.batch_process_documents()
    elif args.process:
        print("NOTE: The --process command is deprecated. Please use --batch-process instead.")
        bizbrain.batch_process_documents()
    elif args.status:
        bizbrain.document_status()
    elif args.question:
        response = bizbrain.answer_question(args.question)
        print(f"\nAnswer: {response['answer']}")
        
        if response['sources']:
            print("\nSources:")
            # Check if sources is a string or a list
            if isinstance(response['sources'], str):
                print(f"- {response['sources']}")
            else:
                for source in response['sources']:
                    print(f"- {source}")
    elif args.interactive or not any([args.batch_process, args.process, args.status, args.question]):
        bizbrain.interactive_mode()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down BizBrain...")
    except Exception as e:
        print(f"\nError: {str(e)}")