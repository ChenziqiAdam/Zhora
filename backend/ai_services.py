# backend/ai_services.py
import openai
import os
import numpy as np
import json
import time # Added import


# Placeholder for OpenAI API Key
# For a real application, retrieve this securely (e.g., environment variables)
openai.api_key = os.getenv("OPENAI_API_KEY")

EMBEDDING_DIMENSION = 1536

async def get_embedding(text: str) -> list[float]:
    """
    Generates an embedding for the given text using OpenAI's embedding model.
    """
    if not openai.api_key:
        print("Warning: OPENAI_API_KEY not set. Returning dummy embedding.")
        return [0.0] * EMBEDDING_DIMENSION  # Dummy embedding for testing

    try:
        response = await openai.Embedding.acreate(
            model="text-embedding-ada-002", # Or a more appropriate model like a multimodal one for images/video
            input=text
        )
        return response['data'][0]['embedding']
    except Exception as e:
        print(f"Error getting embedding from OpenAI: {e}")
        return [0.0] * EMBEDDING_DIMENSION # Fallback to dummy embedding on error

async def analyze_content_with_gpt4o(content: str) -> str:
    """
    Analyzes content using GPT-4o and returns a summary or analysis.
    """
    if not openai.api_key:
        print("Warning: OPENAI_API_KEY not set. Returning dummy analysis.")
        return "Dummy analysis: No OpenAI API key configured."

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o", # Assuming gpt-4o for multimodal analysis
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes project data."},
                {"role": "user", "content": f"Analyze the following project data: {content}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error analyzing content with GPT-4o: {e}")
        return "Dummy analysis: Error during AI analysis."

async def process_media_for_context(file_path: str, file_type: str) -> dict:
    """
    Simulates processing media (video/image) to extract context using GPT-4o.
    """
    if not openai.api_key:
        print("Warning: OPENAI_API_KEY not set. Returning dummy media context.")
        return {"summary": "Dummy media context: No OpenAI API key configured."}

    # In a real scenario, you would extract frames/text from the media file
    # and then send them to GPT-4o for analysis.
    # For now, we'll simulate this.
    simulated_content = f"Simulated content from {file_type} file at {file_path}. Imagine detailed observations about scaffolding issues or project progress."
    
    analysis = await analyze_content_with_gpt4o(simulated_content)
    embedding = await get_embedding(analysis) # Embedding of the analysis
    
    return {
        "summary": analysis,
        "embedding": embedding,
        "timestamp": time.time() # time.time() needs to be imported or passed
    }
