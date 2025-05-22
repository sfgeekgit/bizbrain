#!/usr/bin/env python3
"""
Test script for the delete_empty_batch functionality.

This script:
1. Creates a temporary document registry with test batches
2. Tests deletion of an empty batch (should succeed)
3. Tests deletion of a non-empty batch (should fail)
4. Tests deletion of a non-existent batch (should fail)
"""

import os
import sys
import json
import tempfile
import shutil
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from src.processors.document_loader import DocumentLoader

def setup_test_env():
    """Set up a test environment with a temporary directory structure."""
    temp_dir = tempfile.mkdtemp()
    
    # Create directories needed for testing
    raw_dir = os.path.join(temp_dir, "raw_documents")
    processed_dir = os.path.join(temp_dir, "processed_documents")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(os.path.join(processed_dir, "full_text"), exist_ok=True)
    
    # Create a test registry with one empty and one non-empty batch
    registry = {
        "documents": {
            "test_doc.pdf": {
                "status": "processed",
                "last_processed": datetime.now().isoformat(),
                "document_id": "doc_001",
                "md5_hash": "abc123",
                "batch_id": "batch_002",
                "effective_date": "2023-01-01",
                "chunk_count": 5
            }
        },
        "batches": {
            "batch_001": {
                "created_at": datetime.now().isoformat(),
                "effective_date": "2022-12-01",
                "document_count": 0
            },
            "batch_002": {
                "created_at": datetime.now().isoformat(),
                "effective_date": "2023-01-01",
                "document_count": 1
            }
        },
        "last_update": datetime.now().isoformat(),
        "total_documents": 1,
        "total_chunks": 5,
        "total_batches": 2
    }
    
    # Write registry to file
    registry_path = os.path.join(processed_dir, "document_registry.json")
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    
    return temp_dir, raw_dir, processed_dir

def cleanup_test_env(temp_dir):
    """Clean up the test environment."""
    shutil.rmtree(temp_dir)

def test_delete_empty_batch():
    """Test the delete_empty_batch method."""
    # Set up test environment
    temp_dir, raw_dir, processed_dir = setup_test_env()
    
    try:
        # Initialize DocumentLoader with test directories
        loader = DocumentLoader(raw_dir, processed_dir)
        
        # Test Case 1: Delete an empty batch (should succeed)
        print("\nTest Case 1: Delete an empty batch (should succeed)")
        success, message = loader.delete_empty_batch("batch_001")
        print(f"Success: {success}, Message: {message}")
        
        # Verify batch was deleted
        if "batch_001" not in loader.registry["batches"]:
            print("✓ Empty batch was successfully deleted from registry")
        else:
            print("✗ Failed to delete empty batch from registry")
        
        # Test Case 2: Delete a non-empty batch (should fail)
        print("\nTest Case 2: Delete a non-empty batch (should fail)")
        success, message = loader.delete_empty_batch("batch_002")
        print(f"Success: {success}, Message: {message}")
        
        # Verify batch was not deleted
        if "batch_002" in loader.registry["batches"]:
            print("✓ Non-empty batch was not deleted (as expected)")
        else:
            print("✗ Non-empty batch was incorrectly deleted")
        
        # Test Case 3: Delete a non-existent batch (should fail)
        print("\nTest Case 3: Delete a non-existent batch (should fail)")
        success, message = loader.delete_empty_batch("batch_999")
        print(f"Success: {success}, Message: {message}")
        
        # Verify the registry wasn't changed
        if len(loader.registry["batches"]) == 1:
            print("✓ Registry wasn't affected by attempting to delete non-existent batch")
        else:
            print("✗ Registry was unexpectedly modified")
            
    finally:
        # Clean up
        cleanup_test_env(temp_dir)

if __name__ == "__main__":
    test_delete_empty_batch()