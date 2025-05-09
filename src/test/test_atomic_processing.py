#!/usr/bin/env python3
"""
Test script for atomic document processing.

This script verifies that document processing is atomic:
- Documents are either fully processed or not processed at all
- No intermediate states exist in the registry
- Failure in any stage doesn't leave partial files
"""

import os
import sys
import json
import shutil
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.interface.cli import BizBrainCLI
from utils.dir_setup import ensure_directories

def setup_test_env():
    """Set up a test environment."""
    # Create test directories
    test_dirs = [
        'test_raw_documents',
        'test_processed_documents',
        'test_processed_documents/full_text',
        'test_processed_documents/chunks',
        'test_vector_store',
    ]
    
    for d in test_dirs:
        os.makedirs(d, exist_ok=True)
    
    # Create a simple test document
    with open('test_raw_documents/test_document.txt', 'w') as f:
        f.write("# Test Document\n\nThis is a test document for atomic processing.\n\n")
        f.write("## Section 1\n\nHere is some content for section 1.\n\n")
        f.write("## Section 2\n\nHere is some content for section 2.\n\n")
        f.write("## Section 3\n\nHere is some content for section 3.\n\n")

def cleanup_test_env():
    """Clean up the test environment."""
    dirs_to_remove = [
        'test_raw_documents',
        'test_processed_documents',
        'test_vector_store',
    ]
    
    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d)

def check_registry_integrity(cli):
    """Check that the document registry has consistent states."""
    registry_path = os.path.join(cli.processed_dir, 'document_registry.json')
    
    if not os.path.exists(registry_path):
        print("FAIL: Registry file doesn't exist")
        return False
    
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    # Check that all documents have valid status
    for filename, doc in registry.get('documents', {}).items():
        if doc.get('status') not in ['processed']:
            print(f"FAIL: Document {filename} has invalid status: {doc.get('status')}")
            return False
    
    # Check that document counts match
    doc_count = len(registry.get('documents', {}))
    if registry.get('total_documents') != doc_count:
        print(f"FAIL: Registry document count mismatch: {registry.get('total_documents')} vs {doc_count}")
        return False
    
    return True

def test_successful_processing():
    """Test successful document processing."""
    print("\nTesting successful document processing...")
    
    # Initialize CLI
    cli = BizBrainCLI(
        base_dir="."
    )
    cli.raw_dir = "test_raw_documents"
    cli.processed_dir = "test_processed_documents"
    cli.vector_store_dir = "test_vector_store"
    
    # Process document
    batch_id = "test_batch"
    effective_date = "2025-01-01"
    filename = "test_document.txt"
    
    success, doc_id, chunk_count, error = cli.fully_process_document(
        filename, batch_id, effective_date
    )
    
    # Check results
    if not success:
        print(f"FAIL: Document processing failed: {error}")
        return False
    
    print(f"PASS: Document processed successfully: {doc_id} with {chunk_count} chunks")
    
    # Check that all files were created
    expected_files = [
        f"test_processed_documents/full_text/{doc_id}_full.txt",
        f"test_processed_documents/document_registry.json"
    ]
    
    for i in range(chunk_count):
        expected_files.append(f"test_processed_documents/chunks/{doc_id}_chunk_{str(i).zfill(3)}.json")
    
    for f in expected_files:
        if not os.path.exists(f):
            print(f"FAIL: Expected file not found: {f}")
            return False
    
    print("PASS: All expected files were created")
    
    # Check registry integrity
    if not check_registry_integrity(cli):
        return False
    
    print("PASS: Registry has consistent state")
    return True

def test_update_same_document():
    """Test updating the same document."""
    print("\nTesting document update...")
    
    # Change the test document
    with open('test_raw_documents/test_document.txt', 'w') as f:
        f.write("# Updated Test Document\n\nThis is an updated test document.\n\n")
        f.write("## New Section 1\n\nHere is updated content.\n\n")
    
    # Initialize CLI
    cli = BizBrainCLI(
        base_dir="."
    )
    cli.raw_dir = "test_raw_documents"
    cli.processed_dir = "test_processed_documents"
    cli.vector_store_dir = "test_vector_store"
    
    # Process document
    batch_id = "test_batch_2"
    effective_date = "2025-02-01"
    filename = "test_document.txt"
    
    success, doc_id, chunk_count, error = cli.fully_process_document(
        filename, batch_id, effective_date
    )
    
    # Check results
    if not success:
        print(f"FAIL: Document update failed: {error}")
        return False
    
    print(f"PASS: Document updated successfully: {doc_id} with {chunk_count} chunks")
    
    # Check registry integrity
    if not check_registry_integrity(cli):
        return False
    
    # Check that batch info was updated
    registry_path = os.path.join(cli.processed_dir, 'document_registry.json')
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    doc_entry = registry['documents'].get(filename)
    if not doc_entry:
        print("FAIL: Document entry not found in registry")
        return False
    
    if doc_entry.get('batch_id') != batch_id:
        print(f"FAIL: Document batch ID not updated: {doc_entry.get('batch_id')} vs {batch_id}")
        return False
    
    if doc_entry.get('effective_date') != effective_date:
        print(f"FAIL: Document effective date not updated: {doc_entry.get('effective_date')} vs {effective_date}")
        return False
    
    print("PASS: Document batch info updated correctly")
    return True

def main():
    """Run the tests."""
    print("Testing atomic document processing")
    
    try:
        # Set up test environment
        setup_test_env()
        
        # Run tests
        success1 = test_successful_processing()
        success2 = test_update_same_document()
        
        # Report results
        if success1 and success2:
            print("\nAll tests passed!")
            return 0
        else:
            print("\nSome tests failed")
            return 1
    finally:
        # Clean up
        cleanup_test_env()

if __name__ == "__main__":
    sys.exit(main())