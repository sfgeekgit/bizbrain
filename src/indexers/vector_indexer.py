import os
import json
import numpy as np
import faiss
from langchain_huggingface import HuggingFaceEmbeddings
from utils.config import EMBEDDING_MODEL, EMBEDDING_DIMENSION


class VectorIndexer:
    """Creates and manages vector embeddings for document chunks."""
    
    def __init__(self, processed_dir, vector_store_dir, model_name=EMBEDDING_MODEL):
        self.chunks_dir = os.path.join(processed_dir, 'chunks')
        self.vector_store_dir = vector_store_dir
        self.index_path = os.path.join(vector_store_dir, 'faiss.index')
        self.map_path = os.path.join(vector_store_dir, 'document_to_id_map.json')
        self.model = HuggingFaceEmbeddings(model_name=model_name)
        self.dimension = EMBEDDING_DIMENSION
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load the FAISS index if it exists, or create a new one."""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.map_path):
                # Load existing index
                self.index = faiss.read_index(self.index_path)
                
                # Check if the index supports add_with_ids (should be IndexIDMap)
                if not isinstance(self.index, faiss.IndexIDMap):
                    print("Converting existing index to IndexIDMap for ID support...")
                    # Create a new index with the right type
                    base_index = faiss.IndexFlatL2(self.dimension)
                    new_index = faiss.IndexIDMap(base_index)
                    self.index = new_index
                
                with open(self.map_path, 'r', encoding='utf-8') as f:
                    self.id_to_chunk = json.load(f)
                
                # Convert string keys to integers for internal use
                self.id_to_chunk = {int(k): v for k, v in self.id_to_chunk.items()}
                self.next_id = max(self.id_to_chunk.keys()) + 1 if self.id_to_chunk else 0
            else:
                # Create new index and mapping
                base_index = faiss.IndexFlatL2(self.dimension)  # Simple L2 distance index
                self.index = faiss.IndexIDMap(base_index)  # Wrap with IndexIDMap to support add_with_ids
                self.id_to_chunk = {}
                self.next_id = 0
        except Exception as e:
            # If there's an error, create a new index
            print(f"Error loading index: {str(e)}. Creating a new index...")
            base_index = faiss.IndexFlatL2(self.dimension)  # Simple L2 distance index
            self.index = faiss.IndexIDMap(base_index)  # Wrap with IndexIDMap to support add_with_ids
            self.id_to_chunk = {}
            self.next_id = 0
    
    def _save_index(self):
        """Save the FAISS index and ID mapping."""
        os.makedirs(self.vector_store_dir, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, self.index_path)
        
        # Save ID mapping (convert keys to strings for JSON)
        string_id_map = {str(k): v for k, v in self.id_to_chunk.items()}
        with open(self.map_path, 'w', encoding='utf-8') as f:
            json.dump(string_id_map, f, indent=2)
    
    def get_embedding(self, text):
        """Get embedding for a text string."""
        return self.model.embed_query(text)
    
    def add_document_chunks(self, document_id):
        """Add all chunks from a document to the index."""
        # Get all chunks for this document
        chunk_files = [f for f in os.listdir(self.chunks_dir) 
                      if f.startswith(f"{document_id}_chunk_") and f.endswith('.json')]
        
        if not chunk_files:
            print(f"No chunks found for document {document_id}")
            return 0
        
        embeddings = []
        chunk_data = []
        
        # Process each chunk
        for chunk_file in chunk_files:
            chunk_path = os.path.join(self.chunks_dir, chunk_file)
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunk = json.load(f)
            
            # Generate embedding
            embedding = self.get_embedding(chunk['text'])
            embeddings.append(embedding)
            chunk_data.append({
                'chunk_id': chunk['chunk_id'],
                'metadata': chunk['metadata']
            })
        
        # Convert to numpy array for FAISS
        embeddings_array = np.array(embeddings).astype('float32')
        
        # Add to index
        ids = np.arange(self.next_id, self.next_id + len(embeddings)).astype('int64')
        self.index.add_with_ids(embeddings_array, ids)
        
        # Update mapping
        for i, chunk in enumerate(chunk_data):
            self.id_to_chunk[int(ids[i])] = chunk
        
        self.next_id += len(embeddings)
        
        # Save index
        self._save_index()
        
        return len(embeddings)
    
    def add_embeddings_bulk(self, embeddings, chunk_data):
        """
        Add a batch of embeddings and their corresponding chunk data to the index.
        
        This method handles all numpy operations for bulk embedding addition,
        providing proper separation of concerns by keeping vector operations
        within the VectorIndexer class.
        
        Args:
            embeddings (list): List of embedding vectors
            chunk_data (list): List of dictionaries containing chunk_id and metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not embeddings or not chunk_data:
                return False
                
            if len(embeddings) != len(chunk_data):
                raise ValueError("Embeddings and chunk_data must have the same length")
            
            # Convert to numpy array for FAISS
            embeddings_array = np.array(embeddings).astype('float32')
            
            # Generate IDs for the new embeddings
            ids = np.arange(
                self.next_id, 
                self.next_id + len(embeddings)
            ).astype('int64')
            
            # Add to index
            self.index.add_with_ids(embeddings_array, ids)
            
            # Update mapping
            for i, chunk in enumerate(chunk_data):
                self.id_to_chunk[int(ids[i])] = chunk
            
            self.next_id += len(embeddings)
            
            # Save index
            self._save_index()
            
            return True
            
        except Exception as e:
            print(f"Error adding embeddings to index: {str(e)}")
            return False
    
    def search(self, query_text, top_k=5):
        """Search for similar chunks to the query text."""
        # Get query embedding
        query_embedding = self.get_embedding(query_text)
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search index
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Prepare results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx in self.id_to_chunk:  # -1 means no match
                result = self.id_to_chunk[int(idx)].copy()
                result['score'] = float(distances[0][i])
                results.append(result)
        
        return results
    
    def get_unindexed_documents(self, processed_dir):
        """Get list of documents that have been chunked but not indexed."""
        registry_path = os.path.join(processed_dir, 'document_registry.json')
        if not os.path.exists(registry_path):
            raise FileNotFoundError(f"Document registry not found at {registry_path}")
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        
        # Get all indexed chunk IDs
        indexed_chunks = set()
        for idx, chunk_info in self.id_to_chunk.items():
            indexed_chunks.add(chunk_info['chunk_id'])
        
        # Find documents with unindexed chunks
        unindexed_docs = []
        for filename, entry in registry['documents'].items():
            if entry.get('status') == 'processed' and entry.get('document_id'):
                # Check if all chunks are indexed
                doc_id = entry['document_id']
                # Get first chunk to check if it's indexed
                first_chunk_id = f"{doc_id}_chunk_000"
                if first_chunk_id not in indexed_chunks:
                    unindexed_docs.append(doc_id)
        
        return unindexed_docs


if __name__ == "__main__":
    # Simple test code
    indexer = VectorIndexer(
        processed_dir="processed_documents",
        vector_store_dir="vector_store"
    )
    
    unindexed = indexer.get_unindexed_documents("processed_documents")
    print(f"Found {len(unindexed)} documents to index")
    
    for doc_id in unindexed:
        print(f"Indexing document {doc_id}...")
        num_indexed = indexer.add_document_chunks(doc_id)
        print(f"Indexed {num_indexed} chunks")
    
    # Test search
    if indexer.index.ntotal > 0:  # Only if we have indexed documents
        test_query = "What are the key terms?"
        results = indexer.search(test_query, top_k=3)
        print(f"\nSearch results for '{test_query}':\n")
        for i, result in enumerate(results):
            print(f"Result {i+1}: {result['metadata']['title']} - Section: {result['metadata'].get('section', 'N/A')}")
            print(f"Score: {result['score']}\n")
