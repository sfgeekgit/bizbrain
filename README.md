# BizBrain

A Python-based Q&A system for analyzing legal documents and contracts.


## Overview

BizBrain processes legal documents into searchable chunks, creates vector embeddings, and uses LangChain to answer questions about the documents. The system maintains citations to source documents for verification, enabling accurate answers to complex queries across multiple business and legal documents.

## Key Features

- Cross-document reasoning for complex questions
- Source citations for all answers
- Focus on accuracy over speed
- Designed for internal business use
- Batch document processing with effective dates

## Commands
- Run main script: `python src/main.py`
- Process documents in batches: `python src/main.py --batch-process`
- Check document status: `python src/main.py --status`
- Ask question: `python src/main.py --question "your question"`
- Interactive mode: `python src/main.py --interactive`
- Setup directories: `python src/utils/dir_setup.py`
- Install dependencies: `pip install -r requirements.txt`

> Note: The `--process` command is deprecated and has been replaced by `--batch-process`.


## Project Structure
- `src/`: Main source code with modular architecture
- `raw_documents/`: Original document files (PDF, DOCX)
- `processed_documents/`: Extracted text and chunks
- `vector_store/`: Vector embeddings for retrieval



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

### Directory Structure

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
      "md5_hash": "e8d4e5e2f0a3c1b2d3a4e5f6a7b8c9d0",
      "batch_id": "batch_001",
      "effective_date": "2025-04-12"
    }
  },
  "batches": {
    "batch_001": {
      "created_at": "2025-04-12T14:30:00",
      "effective_date": "2025-04-12",
      "document_count": 1
    }
  },
  "last_update": "2025-04-12T14:32:05",
  "total_documents": 1,
  "total_chunks": 45,
  "total_batches": 1
}
```

This registry enables incremental processing when new documents are added without reprocessing the entire collection. It also tracks document batches with their effective dates.

### Document Processing Flow

1. **Batch Creation**: User creates a batch with an effective date
2. **Document Selection**: User selects which documents to include in the batch
3. **Loading**: Selected documents are loaded from `/raw_documents/`
4. **Extraction**: Text is extracted and cleaned
5. **Storage**: Complete cleaned text saved to /processed_documents/full_text/
6. **Chunking**: Documents are split into semantic chunks with overlap
7. **Metadata Extraction**: Information like document title, section headers, effective date is identified and extracted
8. **Output**: Processed chunks are saved as JSON files in `/processed_documents/chunks/`

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
    "chunk_num": 23,
    "batch_id": "batch_001",
    "effective_date": "2025-04-12",
    "filename": "contract_123.pdf"
  }
}
```

### Incremental Updates

When new documents are added:
1. Only new documents are processed through Layer 1
2. New embeddings are added to the existing vector store in Layer 2
3. Retrieval (Layer 3) and Reasoning (Layer 4) layers automatically incorporate new documents in future queries
4. No changes needed to Interface Layer (Layer 5)

### Batch Processing and Effective Dates

BizBrain supports batch document processing with effective dates:

1. **Interactive Batch Creation**:
   - Users can initiate batch processing with `python src/main.py --batch-process`
   - The system prompts for an effective date in YYYY-MM-DD format
   - Unprocessed documents are displayed, and users can select which to include

2. **Effective Date Handling**:
   - Each document in a batch shares the same effective date
   - The effective date is stored in document metadata and passed to chunks
   - Queries can consider document effective dates for time-sensitive information

3. **Batch Management**:
   - Batches are tracked in the document registry with unique IDs
   - The `document_status` command shows batch information
   - Each document is associated with its batch and effective date

4. **Command-line and Interactive Support**:
   - Batch processing is available both via command-line and interactive mode
   - Interactive mode provides a simple Y/n interface for document selection

### Citation Mechanism

When answering questions, the system:
1. Retrieves relevant chunks from the vector store
2. Provides citations to specific document sections
3. Includes document title, section name, and effective date when available
4. Enables verification by tracing back to original documents