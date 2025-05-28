"""
Interface utilities for BizBrain.
"""

def display_answer_and_sources(response):
    """
    Display an answer and its sources to standard output.
    
    Args:
        response (dict): A dictionary containing 'answer' and 'sources' keys.
            'sources' can be either a string or a list of strings.
            'chunks' is an optional list of retrieved chunks with their metadata.
    """
    print(f"\nAnswer: {response['answer']}")
    
    if response['sources']:
        print("\nSources:")
        # Check if sources is a string or a list
        if isinstance(response['sources'], str):
            print(f"- {response['sources']}")
        else:
            for source in response['sources']:
                print(f"- {source}")
    
    # Display chunks if they exist in the response
    if response.get('chunks'):
        print("\nRetrieved Chunks:")
        for chunk in response['chunks']:
            print(f"\n--- Chunk {chunk['chunk_id']} ---")
            print(f"Document: {chunk['metadata']['title']}")
            print(f"Section: {chunk['metadata'].get('section', 'Unknown')}")
            print(f"Score: {chunk['score']:.4f}")
            print(f"Text:\n{chunk['text']}")  # Show full text 