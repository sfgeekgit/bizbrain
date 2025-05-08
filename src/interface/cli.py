import os
import json
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
        self.document_loader = DocumentLoader(self.raw_dir, self.processed_dir)
        self.text_chunker = TextChunker(self.processed_dir)
        self.vector_indexer = VectorIndexer(self.processed_dir, self.vector_store_dir)
        self.retriever = HybridRetriever(self.processed_dir, self.vector_store_dir)
        self.answer_generator = AnswerGenerator(history_dir=self.history_dir)
    
    def process_documents(self):
        """Process any new or updated documents."""
        print("Checking for new or updated documents...")
        
        # Always initialize document registry by calling get_unprocessed_documents
        # This ensures the registry exists before other components try to use it
        unprocessed = self.document_loader.get_unprocessed_documents()
        
        # Load documents
        if not unprocessed:
            print("No new or updated documents found.")
        else:
            print(f"Found {len(unprocessed)} documents to process.")
            
            for filename in unprocessed:
                print(f"Processing {filename}...")
                result = self.document_loader.process_document(filename)
                if result:
                    doc_id, _ = result
                    print(f"Document extracted as {doc_id}")
        
        # Make sure registry exists before proceeding
        registry_path = os.path.join(self.processed_dir, 'document_registry.json')
        if not os.path.exists(registry_path):
            print("No document registry found. Run document loader first to initialize it.")
            return
        
        # Chunk processed documents
        try:
            docs_to_chunk = self.text_chunker.get_documents_for_chunking()
            if not docs_to_chunk:
                print("No documents need chunking.")
            else:
                print(f"Found {len(docs_to_chunk)} documents to chunk.")
                
                for doc_id, filename in docs_to_chunk:
                    print(f"Chunking document {doc_id} ({filename})...")
                    chunk_count = self.text_chunker.process_document(doc_id, filename)
                    print(f"Created {chunk_count} chunks")
        except FileNotFoundError as e:
            print(f"Error: {str(e)}")
            print("Document loader must be run first to create the registry.")
            return
        
        # Index chunked documents
        try:
            unindexed = self.vector_indexer.get_unindexed_documents(self.processed_dir)
            if not unindexed:
                print("No documents need indexing.")
            else:
                print(f"Found {len(unindexed)} documents to index.")
                
                for doc_id in unindexed:
                    print(f"Indexing document {doc_id}...")
                    num_indexed = self.vector_indexer.add_document_chunks(doc_id)
                    print(f"Indexed {num_indexed} chunks")
        except FileNotFoundError as e:
            print(f"Error: {str(e)}")
            print("Document loader and chunker must be run first.")
            return
                
        print("Document processing complete!")
    
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
    
    def batch_process_documents(self):
        """Process documents in batches with effective dates."""
        print("\nBatch Document Processing")
        print("This will allow you to process documents in batches with effective dates.")
        
        # Ensure registry exists
        if not os.path.exists(self.processed_dir):
            os.makedirs(self.processed_dir, exist_ok=True)
        
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
        
        # Create batch and process documents
        batch_id, processed_docs, failed_docs = self.document_loader.process_batch(
            selected_docs, effective_date)
        
        if not batch_id:
            print("Failed to create batch. No documents processed.")
            return
            
        print(f"\nBatch {batch_id} created with effective date {effective_date}")
        print(f"Processed {len(processed_docs)} documents.")
        
        if failed_docs:
            print(f"Failed to process {len(failed_docs)} documents:")
            for doc in failed_docs:
                print(f"  - {doc}")
        
        # Chunk documents
        try:
            docs_to_chunk = self.text_chunker.get_documents_for_chunking()
            if docs_to_chunk:
                print(f"\nChunking {len(docs_to_chunk)} documents...")
                
                for doc_id, filename in docs_to_chunk:
                    print(f"Chunking document {doc_id} ({filename})...")
                    chunk_count = self.text_chunker.process_document(doc_id, filename)
                    print(f"Created {chunk_count} chunks")
        except FileNotFoundError as e:
            print(f"Error during chunking: {str(e)}")
            return
        
        # Index documents
        try:
            unindexed = self.vector_indexer.get_unindexed_documents(self.processed_dir)
            if unindexed:
                print(f"\nIndexing {len(unindexed)} documents...")
                
                for doc_id in unindexed:
                    print(f"Indexing document {doc_id}...")
                    num_indexed = self.vector_indexer.add_document_chunks(doc_id)
                    print(f"Indexed {num_indexed} chunks")
        except FileNotFoundError as e:
            print(f"Error during indexing: {str(e)}")
            return
        
        print("\nBatch processing complete!")
    
    def document_status(self):
        """Display the status of all documents in the system."""
        registry_path = os.path.join(self.processed_dir, 'document_registry.json')
        if not os.path.exists(registry_path):
            print("No documents have been processed yet.")
            return
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        
        # Show batches if any exist
        if 'batches' in registry and registry['batches']:
            print(f"\nBatches (Total: {registry.get('total_batches', 0)})\n")
            print(f"{'Batch ID':<12} {'Effective Date':<15} {'Created At':<25} {'Document Count':<15}")
            print("-" * 70)
            
            for batch_id, batch in registry['batches'].items():
                effective_date = batch.get('effective_date', 'N/A')
                created_at = batch.get('created_at', 'N/A')
                doc_count = batch.get('document_count', 0)
                
                print(f"{batch_id:<12} {effective_date:<15} {created_at:<25} {doc_count:<15}")
        
        print(f"\nDocument Status (Total: {registry['total_documents']})\n")
        print(f"{'Document ID':<12} {'Status':<15} {'Batch ID':<12} {'Effective Date':<15} {'Chunks':<8} {'Filename':<30}")
        print("-" * 100)
        
        for filename, entry in registry['documents'].items():
            doc_id = entry.get('document_id', 'N/A')
            status = entry.get('status', 'unknown')
            batch_id = entry.get('batch_id', 'N/A')
            effective_date = entry.get('effective_date', 'N/A')
            chunk_count = entry.get('chunk_count', 0)
            
            print(f"{doc_id:<12} {status:<15} {batch_id:<12} {effective_date:<15} {chunk_count:<8} {filename:<30}")
    
    def interactive_mode(self):
        """Run BizBrain in interactive mode."""
        print("\nBizBrain Interactive Mode")
        print("Commands:")
        print("  'exit' - Quit the application")
        print("  'batch' - Process documents in batches with effective dates")
        print("  'status' - See document status")
        print("  Or type your question about documents\n")
        
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
            elif user_input:
                response = self.answer_question(user_input)
                print(f"\nAnswer: {response['answer']}")
                
                if response['sources']:
                    print("\nSources:")
                    # Check if sources is a string or a list
                    if isinstance(response['sources'], str):
                        print(f"- {response['sources']}")
                    else:
                        for source in response['sources']:
                            print(f"- {source}")


if __name__ == "__main__":
    try:
        # Ensure directories exist
        import sys, os
        sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        from utils.dir_setup import ensure_directories
        ensure_directories()
        
        # Create CLI interface
        bizbrain = BizBrainCLI()
        
        # Process documents first
        bizbrain.process_documents()
        
        # Run interactive mode
        bizbrain.interactive_mode()
        
    except KeyboardInterrupt:
        print("\nShutting down BizBrain...")
    except Exception as e:
        print(f"\nError: {str(e)}")
