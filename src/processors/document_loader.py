import os
import json
import hashlib
from datetime import datetime
import PyPDF2
from docx import Document


class DocumentLoader:
    """Loads documents from various formats and extracts text."""
    
    def __init__(self, raw_dir, processed_dir):
        self.raw_dir = raw_dir
        self.full_text_dir = os.path.join(processed_dir, 'full_text')
        self.registry_path = os.path.join(processed_dir, 'document_registry.json')
        self._load_registry()
    
    def _load_registry(self):
        """Load the document registry or create it if it doesn't exist."""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)
        else:
            self.registry = {
                "documents": {},
                "last_update": datetime.now().isoformat(),
                "total_documents": 0,
                "total_chunks": 0
            }
            self._save_registry()
    
    def _save_registry(self):
        """Save the document registry."""
        self.registry["last_update"] = datetime.now().isoformat()
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2)
    
    def _calculate_md5(self, file_path):
        """Calculate MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _extract_text_from_pdf(self, file_path):
        """Extract text from PDF file."""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n\n"
        return text
    
    def _extract_text_from_docx(self, file_path):
        """Extract text from DOCX file."""
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    
    def extract_document_text(self, filename):
        """Extract text from a document based on its file extension."""
        file_path = os.path.join(self.raw_dir, filename)
        _, ext = os.path.splitext(filename)
        
        if ext.lower() == '.pdf':
            return self._extract_text_from_pdf(file_path)
        elif ext.lower() in ['.docx', '.doc']:
            return self._extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def process_document(self, filename):
        """Process a document and save its full text."""
        file_path = os.path.join(self.raw_dir, filename)
        md5_hash = self._calculate_md5(file_path)
        
        # Check if document is already processed and hasn't changed
        if filename in self.registry["documents"] and \
           self.registry["documents"][filename]["md5_hash"] == md5_hash:
            print(f"Document {filename} already processed and unchanged. Skipping.")
            return None
        
        # Extract text based on file type
        try:
            text = self.extract_document_text(filename)
            
            # Create a document ID if it doesn't exist
            if filename not in self.registry["documents"] or \
               "document_id" not in self.registry["documents"][filename]:
                doc_id = f"doc_{str(len(self.registry['documents']) + 1).zfill(3)}"
            else:
                doc_id = self.registry["documents"][filename]["document_id"]
            
            # Save the full text
            full_text_path = os.path.join(self.full_text_dir, f"{doc_id}_full.txt")
            with open(full_text_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Update registry
            self.registry["documents"][filename] = {
                "status": "text_extracted",
                "last_processed": datetime.now().isoformat(),
                "document_id": doc_id,
                "md5_hash": md5_hash
            }
            
            if len(self.registry["documents"]) > self.registry["total_documents"]:
                self.registry["total_documents"] = len(self.registry["documents"])
            
            self._save_registry()
            return doc_id, text
            
        except Exception as e:
            print(f"Error processing document {filename}: {str(e)}")
            return None
    
    def get_unprocessed_documents(self):
        """Get list of documents that need processing."""
        all_files = [f for f in os.listdir(self.raw_dir) 
                    if os.path.isfile(os.path.join(self.raw_dir, f)) and 
                    f.lower().endswith(('.pdf', '.docx', '.doc'))]
        
        unprocessed = []
        for filename in all_files:
            file_path = os.path.join(self.raw_dir, filename)
            md5_hash = self._calculate_md5(file_path)
            
            # Add to unprocessed if file is new or has changed
            if filename not in self.registry["documents"] or \
               self.registry["documents"][filename]["md5_hash"] != md5_hash:
                unprocessed.append(filename)
        
        return unprocessed


if __name__ == "__main__":
    # Simple test code
    loader = DocumentLoader(
        raw_dir="raw_documents",
        processed_dir="processed_documents"
    )
    
    unprocessed = loader.get_unprocessed_documents()
    print(f"Found {len(unprocessed)} documents to process")
    
    for doc in unprocessed:
        print(f"Processing {doc}...")
        result = loader.process_document(doc)
        if result:
            print(f"Processed as {result[0]}")
