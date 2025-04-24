# BizBrain

A Python-based Q&A system for analyzing legal documents and contracts.


## Overview

BizBrain processes legal documents into searchable chunks, creates vector embeddings, and uses LangChain to answer questions about the documents. The system maintains citations to source documents for verification, enabling accurate answers to complex queries across multiple business and legal documents.

## Key Features

- Cross-document reasoning for complex questions
- Source citations for all answers
- Focus on accuracy over speed
- Designed for internal business use

## Directory Structure

- `/raw_documents/` - Original, unprocessed legal documents (contracts, agreements, etc.)
- `/processed_documents/` - Processed document data
  - `/full_text/` - Cleaned and extracted complete text of documents before chunking
  - `/chunks/` - Contains JSON files with chunked text from documents
  - `document_index.json` - Master index of all documents with metadata
  - `document_registry.json` - Tracks processing status of documents
- `/vector_store/` - Storage for vector embeddings
  - `faiss.index` - The vector database (created during processing)
  - `document_to_id_map.json` - Maps between vector IDs and document chunks
- `/conversation_history/` - Records of Q&A interactions with the system
- `/logs/` - System logs for debugging and monitoring
- `/src/` - Python source code
  - `/processors/` - Document processing scripts
  - `/indexers/` - Vector storage and indexing scripts
  - `/retrievers/` - Query and retrieval scripts
  - `/reasoners/` - LLM integration and answer generation
  - `/interface/` - API and UI implementation

## System Architecture

BizBrain is organized into five distinct layers:

1. **Document Processing Layer**
   - Loads documents from various formats
   - Extracts and cleans text
   - Chunks documents into manageable segments
   - Extracts metadata for citation tracking

2. **Storage & Indexing Layer**
   - Creates vector embeddings for text chunks
   - Manages the vector database
   - Stores document metadata
   - Maps between chunks and source documents

3. **Retrieval Layer**
   - Processes user queries
   - Performs hybrid retrieval (semantic + keyword)
   - Re-ranks results for relevance
   - Connects related information across documents

4. **Reasoning Layer**
   - Assembles context from retrieved chunks
   - Integrates with LLM for reasoning
   - Generates answers with citations
   - Tracks sources for verification

5. **Interface Layer**
   - Provides API for internal integration
   - Implements simple user interface
   - Collects feedback for improvement
   - Logs interactions for analysis

## Technology

- Python
- LangChain
- Vector embeddings
- Large Language Models


## Technical Details

### Document Registry

The system tracks document processing status in `/processed_documents/document_registry.json`:

```json
{
  "documents": {
    "contract_123.pdf": {
      "status": "processed",
      "last_processed": "2025-04-12T14:32:05",
      "chunk_count": 45,
      "document_id": "doc_001",
      "md5_hash": "e8d4e5e2f0a3c1b2d3a4e5f6a7b8c9d0"
    }
  },
  "last_update": "2025-04-12T14:32:05",
  "total_documents": 1,
  "total_chunks": 45
}
```

This registry enables incremental processing when new documents are added without reprocessing the entire collection.

### Document Processing Flow

1. **Loading**: Documents are loaded from `/raw_documents/`
2. **Extraction**: Text is extracted and cleaned
3. **Storage**: Complete cleaned text saved to /processed_documents/full_text/
4. **Chunking**: Documents are split into semantic chunks with overlap
5. **Metadata Extraction**: Information like document title, section headers is identified and extracted from document content using NLP techniques
6. **Output**: Processed chunks are saved as JSON files in `/processed_documents/chunks/`

### Chunk Format

Each document chunk is stored in a JSON structure:

```json
{
  "chunk_id": "doc_001_chunk_023",
  "text": "The funding schedule outlined in Section 3.2 requires...",
  "metadata": {
    "document_id": "doc_001",
    "title": "Series A Agreement",
    "section": "Funding Terms",
    "page": 4,
    "paragraph": 2
  }
}
```

### Incremental Updates

When new documents are added:
1. Only new documents are processed through Layer 1
2. New embeddings are added to the existing vector store in Layer 2
3. Retrieval (Layer 3) and Reasoning (Layer 4) layers automatically incorporate new documents in future queries
4. No changes needed to Interface Layer (Layer 5)

### Citation Mechanism

When answering questions, the system:
1. Retrieves relevant chunks from the vector store
2. Provides citations to specific document sections
3. Includes document title, section name, and page number when available
4. Enables verification by tracing back to original documents