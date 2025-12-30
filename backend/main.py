from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import json
import time
import asyncio
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from dotenv import set_key, load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google imports
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Database imports
from database import init_db, get_db_connection

# AI Services imports
from ai_services import process_media_for_context, get_embedding, analyze_content_with_gpt4o

app = FastAPI()

# CORS Middleware
origins = [
    "http://localhost:9999", # Allow frontend origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class OpenAISettings(BaseModel):
    api_key: str

class AskQuery(BaseModel):
    query: str

# OAuth 2.0 scopes for Gmail and Google Drive
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/drive.readonly']

# Placeholder for Google Credentials
CREDENTIALS = None
FLOW = None # Global variable to hold the flow instance

async def process_file_in_background(filename: str):
    print(f"Processing file in background: {filename}")
    
    file_extension = os.path.splitext(filename)[1].lower()
    file_path = f"storage/raw/{filename}"

    # Determine file type for AI processing (simplified)
    if file_extension in ['.mp4', '.mov', '.avi']:
        file_type = "video"
    elif file_extension in ['.png', '.jpg', '.jpeg', '.pdf']:
        file_type = "document" # Treat images and PDFs as documents for now
    else:
        file_type = "unknown"

    # Use AI service to process media for context and embedding
    ai_result = await process_media_for_context(file_path, file_type)
    
    # Create Layer 2 context file
    context_storage_path = "storage/context"
    os.makedirs(context_storage_path, exist_ok=True) # Ensure the directory exists
    context_filename = os.path.join(context_storage_path, f"{os.path.splitext(filename)[0]}.json")
    context_data = {
        "filename": filename, 
        "context": ai_result.get("summary", f"context for {filename}"), 
        "timestamp": ai_result.get("timestamp", time.time())
    }
    with open(context_filename, "w") as f:
        json.dump(context_data, f)
    print(f"Created context file (Layer 2): {context_filename}")

    # Store Layer 3 embedding in the database
    conn = get_db_connection()
    cursor = conn.cursor()
    embedding = ai_result.get("embedding", [])
    embedding_json = json.dumps(embedding)
    
    cursor.execute("INSERT INTO documents (filename, content, embedding) VALUES (?, ?, ?)", 
                   (filename, json.dumps(context_data), embedding_json))
    last_row_id = cursor.lastrowid
    
    # Insert into the virtual table for vector search
    cursor.execute("INSERT INTO documents_vec (rowid, embedding) VALUES (?, ?)", (last_row_id, embedding))
    
    conn.commit()
    conn.close()
    print(f"Stored embedding in database (Layer 3) for {filename}")

async def google_sync_loop():
    while True:
        print("Running Google sync loop...")
        if CREDENTIALS and CREDENTIALS.valid:
            print("Google credentials are valid. Polling Gmail and Google Drive (simulated)...")
        else:
            print("Google credentials not available or invalid. Please authenticate.")
        await asyncio.sleep(600) # Run every 10 minutes (600 seconds)

@app.on_event("startup")
async def startup_event():
    init_db() # Initialize the database
    asyncio.create_task(google_sync_loop()) # Start the Google sync loop as a background task

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/uploadfile/")
async def create_upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    raw_storage_path = "storage/raw"
    os.makedirs(raw_storage_path, exist_ok=True) # Ensure the directory exists
    file_location = os.path.join(raw_storage_path, file.filename)
    
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    background_tasks.add_task(process_file_in_background, file.filename)
    
    return {"filename": file.filename, "message": "File uploaded successfully, processing in background."}

@app.post("/settings/openai_key")
async def save_openai_key(settings: OpenAISettings):
    # Save the API key to a .env file in the backend directory
    set_key(".env", "OPENAI_API_KEY", settings.api_key)
    return {"message": "OpenAI API key saved successfully."}

@app.post("/ask")
async def ask_zhora(query: AskQuery):
    # 1. Get embedding for the user's query
    query_embedding = await get_embedding(query.query)

    # 2. Perform semantic search in the database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Perform a vector search on the documents_vec table
    # This will return the rowids of the top 5 most similar documents
    cursor.execute(
        "SELECT rowid FROM documents_vec WHERE embedding MATCH ? ORDER BY distance LIMIT 5",
        (json.dumps(query_embedding),)
    )
    retrieved_ids = cursor.fetchall()
    
    if not retrieved_ids:
        conn.close()
        return {"answer": "I couldn't find any relevant information in the project memory."}

    # Retrieve the full document details for the found IDs
    doc_ids = [row[0] for row in retrieved_ids]
    cursor.execute(f"SELECT id, filename, content FROM documents WHERE id IN ({','.join('?'*len(doc_ids))})", doc_ids)
    retrieved_docs = cursor.fetchall()
    conn.close()

    if not retrieved_docs:
        return {"answer": "I couldn't find any relevant information in the project memory."}

    # 3. Synthesize an answer with GPT-4o
    context_for_gpt = "Based on the following project data:\n\n"
    for doc in retrieved_docs:
        doc_content = json.loads(doc[2])
        context_for_gpt += f"- Document: {doc[1]}\n  Content: {doc_content.get('context', '')}\n\n"
    
    # Use the actual GPT-4o function from ai_services
    final_answer = await analyze_content_with_gpt4o(f"Answer the following question: '{query.query}' based on this context:\n{context_for_gpt}")

    return {"answer": final_answer, "sources": [doc[1] for doc in retrieved_docs]}

@app.get("/documents")
async def get_documents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, content FROM documents")
    documents = cursor.fetchall()
    conn.close()
    
    # Format the documents as a list of dictionaries
    formatted_docs = []
    for doc in documents:
        formatted_docs.append({
            "id": doc[0],
            "filename": doc[1],
            "content": json.loads(doc[2])
        })
    return formatted_docs

@app.get("/auth/google")
async def google_auth():
    global FLOW
    if not os.path.exists("client_secret.json"):
        raise HTTPException(status_code=400, detail="client_secret.json not found. Please follow Google Cloud setup instructions.")

    FLOW = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    FLOW.redirect_uri = "http://localhost:8000/auth/google/callback" # Ensure this matches your Google Cloud Console setup

    authorization_url, state = FLOW.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return RedirectResponse(url=authorization_url)

@app.get("/auth/google/callback")
async def google_auth_callback(request: Request):
    global CREDENTIALS
    global FLOW

    if FLOW is None:
        raise HTTPException(status_code=400, detail="OAuth flow not initiated. Please go to /auth/google first.")

    # Fetch the token using the authorization response from Google
    try:
        FLOW.fetch_token(authorization_response=str(request.url))
        CREDENTIALS = FLOW.credentials
        
        # Save credentials to a file (e.g., token.json) for persistence
        with open("token.json", "w") as token:
            token.write(CREDENTIALS.to_json())

        return {"message": "Google authentication successful! Credentials stored."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {e}")


