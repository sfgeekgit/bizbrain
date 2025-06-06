import os
import json
import re
import sys
import pathlib
from datetime import datetime
from interface.interface_lib import display_answer_and_sources

root_dir = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

from processors.document_loader import DocumentLoader
from processors.text_chunker import TextChunker
from indexers.vector_indexer import VectorIndexer
from retrievers.hybrid_retriever import HybridRetriever
from reasoners.answer_generator import AnswerGenerator
from utils.config import DEFAULT_RETRIEVAL_TOP_K
from utils.common import load_anthropic_api_key

class BizBrainCLI:
    """Command-line interface for BizBrain."""
    
    def __init__(self, base_dir="."):
        # Set up paths
        self.raw_dir = os.path.join(base_dir, "raw_documents")
        self.processed_dir = os.path.join(base_dir, "processed_documents")
        self.vector_store_dir = os.path.join(base_dir, "vector_store")
        self.history_dir = os.path.join(base_dir, "conversation_history")

        # Load API key from environment or config file
        load_anthropic_api_key()

        # Initialize components
        ##print ("this is slow part?")
        # these next few lines make start up slow, maybe look in to optimizing, or just wait a few seconds.
        self.document_loader = DocumentLoader(self.raw_dir, self.processed_dir)
        self.text_chunker = TextChunker(self.processed_dir)
        self.vector_indexer = VectorIndexer(self.processed_dir, self.vector_store_dir)
        self.retriever = HybridRetriever(self.processed_dir, self.vector_store_dir)
        self.answer_generator = AnswerGenerator(history_dir=self.history_dir)
        # print ("Got it")
        
    
    def answer_question(self, question, top_k=DEFAULT_RETRIEVAL_TOP_K):
        """Answer a question based on the processed documents."""
        print(f"Question: {question}")
        
        # Retrieve relevant chunks
        print("Retrieving relevant information...")
        retrieved_chunks = self.retriever.retrieve_with_context(question, top_k=top_k)
        
        if not retrieved_chunks:
            print("No relevant information found.")
            return {
                "answer": "I don't have enough information to answer this question.",
                "sources": []
            }
        
        # Generate answer
        print("Generating answer...")
        response = self.answer_generator.generate_answer(question, retrieved_chunks)
        
        return response
    
    def fully_process_document(self, filename, batch_id, effective_date):
        """Process a document through the complete pipeline atomically.
        
        This method performs all processing steps (extraction, chunking, indexing)
        in memory first, and only writes files and updates the registry if all
        steps succeed. This ensures that documents are either fully processed
        or not processed at all, with no intermediate states.
        
        The process follows these steps:
        1. Extract text from the document (in memory)
        2. Create chunks from the text (in memory)
        3. Generate embeddings for the chunks (in memory)
        4. If all steps succeed, save all files (text, chunks, index)
        5. Update the document registry as the very last step
        
        If any step fails, no files are written and no updates are made
        to the registry, keeping the system in a consistent state.
        
        Args:
            filename (str): Name of the file to process
            batch_id (str): ID of the batch this document belongs to
            effective_date (str): Effective date for this document (YYYY-MM-DD)
            
        Returns:
            tuple: (success, doc_id, chunk_count, error_msg)
                success (bool): True if processing completed successfully
                doc_id (str): ID of the processed document, or None on failure
                chunk_count (int): Number of chunks created, or 0 on failure
                error_msg (str): Error message if processing failed, or None
        """
        try:
            print(f"Processing {filename} in batch {batch_id}...")
            
            # Step 1: Extract document text (but don't save yet)
            file_path = os.path.join(self.raw_dir, filename)
            md5_hash = self.document_loader._calculate_md5(file_path)
            
            # Check if document is already processed and unchanged
            if filename in self.document_loader.registry["documents"] and \
                self.document_loader.registry["documents"][filename]["md5_hash"] == md5_hash and \
                self.document_loader.registry["documents"][filename]["status"] == "processed":
                print(f"Document {filename} already fully processed and unchanged. Skipping.")
                doc_id = self.document_loader.registry["documents"][filename]["document_id"]
                chunk_count = self.document_loader.registry["documents"][filename].get("chunk_count", 0)
                return True, doc_id, chunk_count, None
            
            # Extract text based on file type
            text = self.document_loader.extract_document_text(filename)
            
            # Create a document ID
            if filename not in self.document_loader.registry["documents"] or \
                "document_id" not in self.document_loader.registry["documents"][filename]:
                doc_id = f"doc_{str(len(self.document_loader.registry['documents']) + 1).zfill(3)}"
            else:
                doc_id = self.document_loader.registry["documents"][filename]["document_id"]
            
            # Step 2: Create chunks in memory
            # Extract metadata
            metadata = {
                "document_id": doc_id,
                "title": filename,  # Simplified - real metadata extraction happens in TextChunker
                "filename": filename,
                "batch_id": batch_id,
                "effective_date": effective_date
            }
            
            # Create chunks (similar to TextChunker._chunk_text but we don't save them yet)
            chunks = []
            start = 0
            chunk_num = 0
            
            while start < len(text):
                # Get chunk of text
                end = min(start + self.text_chunker.chunk_size, len(text))
                chunk_text = text[start:end]
                
                # Create chunk ID
                chunk_id = f"{doc_id}_chunk_{str(chunk_num).zfill(3)}"
                
                # Try to find a section header
                section_match = re.search(r'#+\s*(.+?)\n', chunk_text[:min(200, len(chunk_text))])
                section = section_match.group(1).strip() if section_match else "Unknown section"
                
                # Create chunk metadata
                chunk_metadata = metadata.copy()
                chunk_metadata["section"] = section
                chunk_metadata["chunk_num"] = chunk_num
                
                # Create chunk object
                chunk = {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "metadata": chunk_metadata
                }
                
                chunks.append(chunk)
                
                # Move to next chunk with overlap
                start = end - self.text_chunker.chunk_overlap if end < len(text) else len(text)
                chunk_num += 1
            
            # Step 3: Create embeddings in memory
            embeddings = []
            chunk_data = []
            
            for chunk in chunks:
                # Generate embedding
                embedding = self.vector_indexer.get_embedding(chunk['text'])
                embeddings.append(embedding)
                chunk_data.append({
                    'chunk_id': chunk['chunk_id'],
                    'metadata': chunk['metadata']
                })
            
            # All in-memory processing succeeded, now we can write to disk
            
            # Step 4: Save the full text
            full_text_path = os.path.join(self.text_chunker.full_text_dir, f"{doc_id}_full.txt")
            os.makedirs(os.path.dirname(full_text_path), exist_ok=True)
            with open(full_text_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Step 5: Save chunks
            os.makedirs(self.text_chunker.chunks_dir, exist_ok=True)
            for chunk in chunks:
                chunk_path = os.path.join(self.text_chunker.chunks_dir, f"{chunk['chunk_id']}.json")
                with open(chunk_path, 'w', encoding='utf-8') as f:
                    json.dump(chunk, f, indent=2)
            
            # Step 6: Update vector index
            if embeddings:
                # Add embeddings to index using VectorIndexer's bulk method
                success = self.vector_indexer.add_embeddings_bulk(embeddings, chunk_data)
                if not success:
                    raise Exception("Failed to add embeddings to vector index")
            
            # Step 7: Update document registry
            registry = self.document_loader.registry
            
            # Update document entry
            doc_entry = {
                "status": "processed",  # Directly mark as fully processed
                "last_processed": datetime.now().isoformat(),
                "document_id": doc_id,
                "md5_hash": md5_hash,
                "batch_id": batch_id,
                "effective_date": effective_date,
                "chunk_count": len(chunks)
            }
            
            registry["documents"][filename] = doc_entry
            
            # Update batch document count
            if "batches" in registry and batch_id in registry["batches"]:
                registry["batches"][batch_id]["document_count"] += 1
            
            # Update total counts
            if len(registry["documents"]) > registry["total_documents"]:
                registry["total_documents"] = len(registry["documents"])
            
            registry["total_chunks"] = sum(
                doc.get("chunk_count", 0) for doc in registry["documents"].values()
            )
            
            # Save the registry
            self.document_loader._save_registry()
            
            return True, doc_id, len(chunks), None
            
        except Exception as e:
            error_msg = f"Error processing document {filename}: {str(e)}"
            print(error_msg)
            return False, None, 0, error_msg
    
    def batch_process_documents(self):
        """Process documents in batches with effective dates."""
        print("\nBatch Document Processing")
        print("This will allow you to process documents in batches with effective dates.")
        
        # Ensure registry exists
        if not os.path.exists(self.processed_dir):
            os.makedirs(self.processed_dir, exist_ok=True)
            os.makedirs(os.path.join(self.processed_dir, 'full_text'), exist_ok=True)
            os.makedirs(os.path.join(self.processed_dir, 'chunks'), exist_ok=True)
        
        # Get unprocessed documents
        unprocessed = self.document_loader.get_unprocessed_documents()
        
        if not unprocessed:
            print("No new or updated documents found to process.")
            return
        
        print(f"Found {len(unprocessed)} documents that need processing.")
        
        # Get effective date from user
        while True:
            effective_date = input("Enter effective date for this batch (YYYY-MM-DD): ").strip()
            
            if self.document_loader.validate_date_format(effective_date):
                break
            else:
                print("Invalid date format. Please use YYYY-MM-DD format.")
        
        # Select documents for this batch
        selected_docs = []
        
        print("\nSelect documents to include in this batch:")
        for i, filename in enumerate(unprocessed, 1):
            while True:
                choice = input(f"{i}. {filename} (Y/n): ").strip().lower()
                
                if choice in ('', 'y', 'yes'):
                    selected_docs.append(filename)
                    break
                elif choice in ('n', 'no'):
                    break
                else:
                    print("Please enter Y or n.")
        
        if not selected_docs:
            print("No documents selected for processing. Exiting batch process.")
            return
        
        print(f"\nProcessing {len(selected_docs)} documents with effective date: {effective_date}")
        
        # Create a new batch
        batch_id = self.document_loader.create_batch(effective_date)
        if not batch_id:
            print("Failed to create batch. No documents processed.")
            return
        
        # Process each document atomically
        processed_docs = []
        failed_docs = []
        
        for filename in selected_docs:
            success, doc_id, chunk_count, error_msg = self.fully_process_document(
                filename, batch_id, effective_date
            )
            
            if success:
                processed_docs.append((doc_id, filename, chunk_count))
                print(f"✓ Document {filename} fully processed with {chunk_count} chunks")
            else:
                failed_docs.append((filename, error_msg))
                print(f"✗ Failed to process {filename}: {error_msg}")
        
        # Report results
        print(f"\nBatch {batch_id} processed with effective date {effective_date}")
        print(f"Successfully processed {len(processed_docs)} documents")
        
        if failed_docs:
            print(f"Failed to process {len(failed_docs)} documents:")
            for doc, err in failed_docs:
                print(f"  - {doc}: {err}")
        
        print("\nBatch processing complete!")
    
    def get_document_status(self):
        """
        Get the status of all documents in the system as structured data.
        
        Returns:
            dict: A dictionary containing document registry information or None if no documents found
                {
                    'registry_info': {total_documents, total_chunks, total_batches, last_update},
                    'batches': [
                        {batch_id, effective_date, created_at, document_count}
                    ],
                    'documents': [
                        {document_id, status, batch_id, effective_date, chunk_count, filename}
                    ]
                }
        """
        registry_path = os.path.join(self.processed_dir, 'document_registry.json')
        if not os.path.exists(registry_path):
            return None
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        
        # Prepare structured data
        result = {
            'registry_info': {
                'total_documents': registry.get('total_documents', 0),
                'total_chunks': registry.get('total_chunks', 0),
                'total_batches': registry.get('total_batches', 0),
                'last_update': registry.get('last_update', 'N/A')
            },
            'batches': [],
            'documents': []
        }
        
        # Process batches
        if 'batches' in registry:
            for batch_id, batch in registry['batches'].items():
                result['batches'].append({
                    'batch_id': batch_id,
                    'effective_date': batch.get('effective_date', 'N/A'),
                    'created_at': batch.get('created_at', 'N/A'),
                    'document_count': batch.get('document_count', 0)
                })
        
        # Process documents
        if 'documents' in registry:
            for filename, entry in registry['documents'].items():
                result['documents'].append({
                    'document_id': entry.get('document_id', 'N/A'),
                    'status': entry.get('status', 'unknown'),
                    'batch_id': entry.get('batch_id', 'N/A'),
                    'effective_date': entry.get('effective_date', 'N/A'),
                    'chunk_count': entry.get('chunk_count', 0),
                    'filename': filename
                })
        
        # Sort batches by batch_id
        result['batches'].sort(key=lambda x: x['batch_id'])
        
        # Sort documents by document_id
        result['documents'].sort(key=lambda x: x['document_id'])
        
        return result
    
    def document_status(self):
        """Display the status of all documents in the system to the console."""
        status_data = self.get_document_status()
        
        if not status_data:
            print("No documents have been processed yet.")
            return
        
        # Show batches if any exist
        if status_data['batches']:
            print(f"\nBatches (Total: {status_data['registry_info']['total_batches']})\n")
            print(f"{'Batch ID':<12} {'Effective Date':<15} {'Created At':<25} {'Document Count':<15}")
            print("-" * 70)
            
            for batch in status_data['batches']:
                print(f"{batch['batch_id']:<12} {batch['effective_date']:<15} {batch['created_at']:<25} {batch['document_count']:<15}")
        
        # Show documents
        print(f"\nDocument Status (Total: {status_data['registry_info']['total_documents']})\n")
        print(f"{'Document ID':<12} {'Status':<15} {'Batch ID':<12} {'Effective Date':<15} {'Chunks':<8} {'Filename':<30}")
        print("-" * 100)
        
        for doc in status_data['documents']:
            print(f"{doc['document_id']:<12} {doc['status']:<15} {doc['batch_id']:<12} {doc['effective_date']:<15} {doc['chunk_count']:<8} {doc['filename']:<30}")
    
    def display_help(self):
        """Display the list of available commands."""
        print("\nBizBrain Commands:")
        print("  'help' - Display this help information")
        print("  'exit' - Quit the application")
        print("  'batch' - Process documents in batches with effective dates")
        print("  'status' - See document status")
        print("  'delete-batch BATCH_ID' - Delete an empty batch")
        print("  Or type your question about documents")
    
    def interactive_mode(self):
        """Run BizBrain in interactive mode."""
        print("\nBizBrain Interactive Mode")
        self.display_help()
        
        # Check for API key
        key_available = load_anthropic_api_key()
        if not key_available:
            print("\n⚠️  IMPORTANT: The ANTHROPIC_API_KEY is not available.")
            print("To enable answering questions, please either:")
            print("    1. Set the ANTHROPIC_API_KEY environment variable, or")
            print("    2. Add your API key to the config_env.py file in the project root")
            print("\nYou can still use 'batch' and 'status' commands without an API key.\n")
        
        while True:
            user_input = input("\nEnter a command or question: ").strip()
            
            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            elif user_input.lower() == 'batch':
                self.batch_process_documents()
            elif user_input.lower() == 'status':
                self.document_status()
            elif user_input.lower() == 'help':
                self.display_help()
            elif user_input.lower().startswith('delete-batch '):
                batch_id = user_input[len('delete-batch '):].strip()
                if not batch_id:
                    print("Error: Please provide a batch ID (e.g., 'delete-batch batch_001')")
                else:
                    success, message = self.document_loader.delete_empty_batch(batch_id)
                    if success:
                        print(f"Successfully deleted empty batch {batch_id}")
                    else:
                        print(f"Error: {message}")
            elif user_input:
                response = self.answer_question(user_input)
                display_answer_and_sources(response)


if __name__ == "__main__":
    try:
        # Ensure directories exist
        import sys, os
        sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        from utils.dir_setup import ensure_directories
        ensure_directories()
        
        # Create CLI interface
        bizbrain = BizBrainCLI()
        
        # Run interactive mode
        bizbrain.interactive_mode()
        
    except KeyboardInterrupt:
        print("\nShutting down BizBrain...")
    except Exception as e:
        print(f"\nError: {str(e)}")
