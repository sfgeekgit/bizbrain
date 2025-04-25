import os
import json
from datetime import datetime
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from utils.config import LLM_MODEL, LLM_TEMPERATURE
from utils.common import load_anthropic_api_key


class AnswerGenerator:
    """Generates answers to questions using LLM and retrieved document chunks."""
    
    def __init__(self, model_name=LLM_MODEL, temperature=LLM_TEMPERATURE, history_dir="conversation_history"):
        # Use the specified model or fall back to config defaults
        # Try to load API key from environment or config file
        key_available = load_anthropic_api_key()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not key_available:
            print("Warning: ANTHROPIC_API_KEY not found in environment or config file. Using placeholder for development.")
            api_key = "placeholder_api_key"  # This is just for code to run, will generate errors on actual API calls
        self.llm = ChatAnthropic(model=model_name, temperature=temperature, api_key=api_key)
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        
        # Define output schema for structured responses
        self.response_schemas = [
            ResponseSchema(name="answer", description="The answer to the user's question"),
            ResponseSchema(name="sources", description="The sources used to generate the answer")
        ]
        self.output_parser = StructuredOutputParser.from_response_schemas(self.response_schemas)
        self.format_instructions = self.output_parser.get_format_instructions()
        
        # Create system prompt template
        self.prompt_template = ChatPromptTemplate.from_template(
            """You are BizBrain, an assistant that answers questions about legal documents and contracts.\n\n
            CONTEXT INFORMATION:\n\n{context}\n\n
            Based on the context information, answer the question below. If the answer is not contained within the 
            context, respond with "I don't have enough information to answer this question."
            
            Include specific citations to the source documents in your answer. Citations should be in the format:
            [Document Title, Section Name] at the end of the relevant sentence or paragraph.
            
            Question: {question}\n\n
            {format_instructions}
            """
        )
    
    def _format_context(self, retrieved_chunks):
        """Format retrieved chunks into context for the LLM."""
        context_parts = []
        
        for i, chunk in enumerate(retrieved_chunks):
            # Format the metadata for citation
            doc_title = chunk['metadata'].get('title', 'Unnamed Document')
            section = chunk['metadata'].get('section', 'Unknown Section')
            
            context_parts.append(f"--- Document {i+1}: {doc_title} - {section} ---\n{chunk['text']}\n")
        
        return "\n\n".join(context_parts)
    
    def _save_conversation(self, question, answer, sources, retrieved_chunks):
        """Save the conversation to history."""
        timestamp = datetime.now().isoformat()
        filename = f"conversation_{timestamp.replace(':', '-')}.json"
        filepath = os.path.join(self.history_dir, filename)
        
        conversation = {
            "timestamp": timestamp,
            "question": question,
            "answer": answer,
            "sources": sources,
            "retrieved_chunks": [
                {
                    "chunk_id": chunk["chunk_id"],
                    "metadata": chunk["metadata"],
                    "score": chunk["score"]
                } for chunk in retrieved_chunks
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, indent=2)
    
    def generate_answer(self, question, retrieved_chunks):
        """Generate an answer to the question based on retrieved chunks."""
        if not retrieved_chunks:
            answer = "I don't have enough information to answer this question."
            sources = []
            self._save_conversation(question, answer, sources, [])
            return {"answer": answer, "sources": sources}
        
        # Format context from retrieved chunks
        context = self._format_context(retrieved_chunks)
        
        # Generate the answer
        prompt = self.prompt_template.format(
            context=context,
            question=question,
            format_instructions=self.format_instructions
        )
        
        # Call the LLM
        response = self.llm.invoke(prompt)
        parsed_response = self.output_parser.parse(response.content)
        
        # Save the conversation
        self._save_conversation(
            question, 
            parsed_response["answer"], 
            parsed_response["sources"],
            retrieved_chunks
        )
        
        return parsed_response


if __name__ == "__main__":
    # This is just a test - in a real application you'd need actual retrieved chunks
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from retrievers.hybrid_retriever import HybridRetriever
    
    retriever = HybridRetriever(
        processed_dir="processed_documents",
        vector_store_dir="vector_store"
    )
    
    generator = AnswerGenerator()
    
    test_questions = [
        "What are the terms for Series A funding?",
        "Who is on the board of directors?"
    ]
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        retrieved_chunks = retriever.retrieve_with_context(question, top_k=3)
        
        if retrieved_chunks:
            response = generator.generate_answer(question, retrieved_chunks)
            print(f"\nAnswer: {response['answer']}")
            print("\nSources:")
            for source in response['sources']:
                print(f"- {source}")
        else:
            print("No relevant documents found.")
