import os
import json
import re
from datetime import datetime
from utils.config import CHUNK_SIZE, CHUNK_OVERLAP


class TextChunker:
    """Chunks documents into smaller segments for processing."""
    
    def __init__(self, processed_dir, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
        self.full_text_dir = os.path.join(processed_dir, 'full_text')
        self.chunks_dir = os.path.join(processed_dir, 'chunks')
        self.registry_path = os.path.join(processed_dir, 'document_registry.json')
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._load_registry()
    
    def _load_registry(self):
        """Load the document registry."""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)
        else:
            raise FileNotFoundError(f"Document registry not found at {self.registry_path}")
    
    def _save_registry(self):
        """Save the document registry."""
        self.registry["last_update"] = datetime.now().isoformat()
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2)
    
    def _extract_metadata(self, text, document_id, filename, doc_entry=None):
        """Extract metadata from document text.
        This is a simplified version - in a real system, this would be more sophisticated.
        
        Args:
            text (str): Document text
            document_id (str): Document ID
            filename (str): Document filename
            doc_entry (dict, optional): Document entry from registry
            
        Returns:
            dict: Document metadata
        """
        # Try to extract a title
        title_match = re.search(r'^#*\s*(.+?)\n', text) or re.search(r'^(.+?)\n', text)
        title = title_match.group(1) if title_match else filename
        
        # Basic metadata
        metadata = {
            "document_id": document_id,
            "title": title.strip(),
            "filename": filename
        }
        
        # Add batch information if available
        if doc_entry:
            if "batch_id" in doc_entry:
                metadata["batch_id"] = doc_entry["batch_id"]
            
            if "effective_date" in doc_entry:
                metadata["effective_date"] = doc_entry["effective_date"]
        
        return metadata
    
    def _chunk_text(self, text, metadata, document_id):
        """Chunk text into smaller segments."""
        chunks = []
        
        # Simple chunking by characters with overlap
        # A more sophisticated implementation would chunk by sentences or paragraphs
        start = 0
        chunk_num = 0
        
        while start < len(text):
            # Get chunk of text
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            
            # Create chunk ID
            chunk_id = f"{document_id}_chunk_{str(chunk_num).zfill(3)}"
            
            # Try to find a section header near the start of the chunk
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
            start = end - self.chunk_overlap if end < len(text) else len(text)
            chunk_num += 1
        
        return chunks
    
    def process_document(self, document_id, filename):
        """Process a document into chunks."""
        # Find document in registry
        doc_entry = None
        for fname, entry in self.registry["documents"].items():
            if entry.get("document_id") == document_id:
                doc_entry = entry
                filename = fname
                break
        
        if not doc_entry:
            raise ValueError(f"Document ID {document_id} not found in registry")
        
        # Skip if already chunked
        if doc_entry.get("status") == "processed":
            print(f"Document {filename} already chunked. Skipping.")
            return doc_entry.get("chunk_count", 0)
        
        # Load full text
        full_text_path = os.path.join(self.full_text_dir, f"{document_id}_full.txt")
        if not os.path.exists(full_text_path):
            raise FileNotFoundError(f"Full text not found for document {document_id}")
        
        with open(full_text_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Extract metadata, including batch and effective date if available
        metadata = self._extract_metadata(text, document_id, filename, doc_entry)
        
        # Chunk the text
        chunks = self._chunk_text(text, metadata, document_id)
        
        # Save chunks
        for chunk in chunks:
            chunk_path = os.path.join(self.chunks_dir, f"{chunk['chunk_id']}.json")
            with open(chunk_path, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, indent=2)
        
        # Update registry
        doc_entry["status"] = "processed"
        doc_entry["last_processed"] = datetime.now().isoformat()
        doc_entry["chunk_count"] = len(chunks)
        
        # Update total chunks
        self.registry["total_chunks"] = sum(doc.get("chunk_count", 0) 
                                        for doc in self.registry["documents"].values())
        
        self._save_registry()
        return len(chunks)
    
    def get_documents_for_chunking(self):
        """Get documents that have been text-extracted but not chunked."""
        docs_to_chunk = []
        for filename, entry in self.registry["documents"].items():
            if entry.get("status") == "text_extracted":
                docs_to_chunk.append((entry["document_id"], filename))
        return docs_to_chunk


if __name__ == "__main__":
    # Simple test code
    chunker = TextChunker(processed_dir="processed_documents")
    
    docs_to_chunk = chunker.get_documents_for_chunking()
    print(f"Found {len(docs_to_chunk)} documents to chunk")
    
    for doc_id, filename in docs_to_chunk:
        print(f"Chunking document {doc_id} ({filename})...")
        chunk_count = chunker.process_document(doc_id, filename)
        print(f"Created {chunk_count} chunks")
