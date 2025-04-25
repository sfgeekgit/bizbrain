import os
import json
import re
from indexers.vector_indexer import VectorIndexer
from utils.config import DEFAULT_RETRIEVAL_TOP_K


class HybridRetriever:
    """Retrieves relevant document chunks using hybrid search."""
    
    def __init__(self, processed_dir, vector_store_dir):
        self.processed_dir = processed_dir
        self.chunks_dir = os.path.join(processed_dir, 'chunks')
        self.vector_indexer = VectorIndexer(processed_dir, vector_store_dir)
    
    def _keyword_search(self, query, top_k=DEFAULT_RETRIEVAL_TOP_K*2):
        """Simple keyword search on chunks."""
        # Extract key terms from query (simple approach)
        query_terms = set(re.findall(r'\w+', query.lower()))
        query_terms = {term for term in query_terms if len(term) > 3}  # Filter short words
        
        if not query_terms:
            return []  # No significant terms to search for
        
        # Search all chunks (in a real system, this would use a proper inverted index)
        chunk_scores = {}
        
        for file in os.listdir(self.chunks_dir):
            if not file.endswith('.json'):
                continue
                
            chunk_path = os.path.join(self.chunks_dir, file)
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunk = json.load(f)
            
            # Count matching terms
            text_lower = chunk['text'].lower()
            score = sum(1 for term in query_terms if term in text_lower)
            
            if score > 0:
                chunk_scores[chunk['chunk_id']] = {
                    'chunk_id': chunk['chunk_id'],
                    'metadata': chunk['metadata'],
                    'score': score
                }
        
        # Sort by score and return top_k
        results = sorted(chunk_scores.values(), key=lambda x: x['score'], reverse=True)[:top_k]
        return results
    
    def retrieve(self, query, top_k=DEFAULT_RETRIEVAL_TOP_K, use_hybrid=True):
        """Retrieve documents using semantic and optionally keyword search."""
        # Get semantic search results
        semantic_results = self.vector_indexer.search(query, top_k=top_k*2)  # Get more for reranking
        
        if not use_hybrid:
            return semantic_results[:top_k]
        
        # Get keyword search results
        keyword_results = self._keyword_search(query, top_k=top_k*2)
        
        # Combine results (simple approach - in a real system use a more sophisticated reranking)
        combined_results = {}
        
        # Add semantic results with their scores
        for result in semantic_results:
            combined_results[result['chunk_id']] = {
                'chunk_id': result['chunk_id'],
                'metadata': result['metadata'],
                'semantic_score': result['score'],
                'keyword_score': 0,
                'combined_score': result['score']  # Initialize with semantic score
            }
        
        # Add or update with keyword results
        for result in keyword_results:
            chunk_id = result['chunk_id']
            keyword_score = result['score'] / max(1, len(result['chunk_id']))  # Normalize
            
            if chunk_id in combined_results:
                combined_results[chunk_id]['keyword_score'] = keyword_score
                # Simple combination - multiply scores (lower is better for semantic, higher for keyword)
                combined_results[chunk_id]['combined_score'] = (
                    combined_results[chunk_id]['semantic_score'] * (1 - 0.3 * keyword_score)
                )
            else:
                combined_results[chunk_id] = {
                    'chunk_id': chunk_id,
                    'metadata': result['metadata'],
                    'semantic_score': float('inf'),  # High (bad) semantic score
                    'keyword_score': keyword_score,
                    'combined_score': float('inf') * (1 - 0.3 * keyword_score)  # Adjust by keyword
                }
        
        # Sort by combined score (lower is better) and return top_k
        results = sorted(combined_results.values(), key=lambda x: x['combined_score'])[:top_k]
        
        # Cleanup for return - rename combined_score to score
        for result in results:
            result['score'] = result['combined_score']
            del result['combined_score']
            del result['semantic_score']
            del result['keyword_score']
        
        return results
    
    def get_chunk_text(self, chunk_id):
        """Get the text for a specific chunk ID."""
        chunk_path = os.path.join(self.chunks_dir, f"{chunk_id}.json")
        
        if not os.path.exists(chunk_path):
            return None
            
        with open(chunk_path, 'r', encoding='utf-8') as f:
            chunk = json.load(f)
            
        return chunk['text']
    
    def retrieve_with_context(self, query, top_k=DEFAULT_RETRIEVAL_TOP_K):
        """Retrieve documents and include their text content."""
        results = self.retrieve(query, top_k=top_k)
        
        # Add the actual text content to results
        for result in results:
            result['text'] = self.get_chunk_text(result['chunk_id'])
            
        return results


if __name__ == "__main__":
    # Simple test code
    retriever = HybridRetriever(
        processed_dir="processed_documents",
        vector_store_dir="vector_store"
    )
    
    test_query = "What are the terms for Series A funding?"
    
    print(f"Testing query: '{test_query}'")
    results = retriever.retrieve_with_context(test_query, top_k=3)
    
    print(f"Found {len(results)} results:\n")
    for i, result in enumerate(results):
        print(f"Result {i+1}: {result['metadata']['title']} - Section: {result['metadata'].get('section', 'N/A')}")
        print(f"Score: {result['score']}")
        print(f"Excerpt: {result['text'][:200]}...\n")
