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
    
    def document_status(self):
        """Display the status of all documents in the system."""
        registry_path = os.path.join(self.processed_dir, 'document_registry.json')
        if not os.path.exists(registry_path):
            print("No documents have been processed yet.")
            return
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        
        print(f"\nDocument Status (Total: {registry['total_documents']})\n")
        print(f"{'Document ID':<12} {'Status':<15} {'Last Processed':<25} {'Chunks':<10} {'Filename':<30}")
        print("-" * 90)
        
        for filename, entry in registry['documents'].items():
            doc_id = entry.get('document_id', 'N/A')
            status = entry.get('status', 'unknown')
            last_processed = entry.get('last_processed', 'N/A')
            chunk_count = entry.get('chunk_count', 0)
            
            print(f"{doc_id:<12} {status:<15} {last_processed:<25} {chunk_count:<10} {filename:<30}")
    
    def interactive_mode(self):
        """Run BizBrain in interactive mode."""
        print("\nBizBrain Interactive Mode")
        print("Type 'exit' to quit, 'process' to process documents, 'status' to see document status\n")
        
        # Check for API key
        key_available = load_anthropic_api_key()
        if not key_available:
            print("\n⚠️  IMPORTANT: The ANTHROPIC_API_KEY is not available.")
            print("To enable answering questions, please either:")
            print("    1. Set the ANTHROPIC_API_KEY environment variable, or")
            print("    2. Add your API key to the config_env.py file in the project root")
            print("\nYou can still use 'process' and 'status' commands without an API key.\n")
        
        while True:
            user_input = input("\nEnter your question: ").strip()
            
            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            elif user_input.lower() == 'process':
                self.process_documents()
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
