# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Run main script: `python src/main.py`
- Process documents: `python src/main.py --process`
- Check document status: `python src/main.py --status`
- Ask question: `python src/main.py --question "your question"`
- Interactive mode: `python src/main.py --interactive`
- Setup directories: `python src/utils/dir_setup.py`
- Install dependencies: `pip install -r requirements.txt`

## Code Style Guidelines
- Indentation: 4 spaces
- Imports: system first, third-party second, project modules last
- Strings: double quotes for docstrings, single quotes for strings
- Classes: CamelCase (DocumentLoader)
- Functions/methods: snake_case (process_document)
- Private methods: prefix with underscore (_load_registry)
- Constants: UPPER_CASE (DEFAULT_RETRIEVAL_TOP_K)
- Error handling: Use try-except blocks, catch KeyboardInterrupt for clean exit
- Documentation: Include docstrings for classes and methods
- Type hints: Use for function parameters and return values

## Project Structure
- `src/`: Main source code with modular architecture
- `raw_documents/`: Original document files (PDF, DOCX)
- `processed_documents/`: Extracted text and chunks
- `vector_store/`: Vector embeddings for retrieval