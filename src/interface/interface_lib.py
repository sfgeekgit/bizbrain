"""
Interface utilities for BizBrain.
"""

def display_answer_and_sources(response):
    """
    Display an answer and its sources in the standard format.
    
    Args:
        response (dict): A dictionary containing 'answer' and 'sources' keys.
            'sources' can be either a string or a list of strings.
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