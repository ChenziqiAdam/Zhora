## 1. Product Overview: Mortar Zhora 0.1 MVP

**Mortar Zhora** is a contextual AI platform that transforms fragmented project data—video, text, and emails—into a unified project memory.

### Core Value Proposition

- **Unified Project Memory:** Automatically ingests and normalizes site walks (video), reports (text), and communications (Gmail).
    
- **Aegis Video Layer:** A dedicated tab for raw sensory data, allowing Zhora to detect trends and trigger actions from video observations.
    
- **Zero-Configuration AI:** Replaces manual dashboards and spreadsheets with a single "Ask Zhora" command bar.

---

## 2. Technical Architecture & Tech Stack

To build this simply without AWS or n8n, we utilize a **Local-First RAG (Retrieval-Augmented Generation)** architecture.

|**Layer**|**Technology**|**Function**|
|---|---|---|
|**Frontend**|**Next.js**|The user interface (Command Bar, Dashboard, Aegis video player).|
|**Backend**|**FastAPI (Python)**|The "Glue" that handles file uploads, background processing, and AI calls.|
|**Memory (L1/L2)**|**Local File System**|Stores raw videos/PDFs and extracted context frames locally on disk.|
|**Memory (L3)**|**SQLite + `sqlite-vec`**|A lightweight, embedded database for both relational metadata and vector embeddings.|
|**Integrations**|**Google Client Libs**|Official Python libraries to poll and pull data from Gmail and Google Drive.|
|**Reasoning**|**GPT-4o API**|Multimodal AI that analyzes video frames and summarizes project trends.|

---

## 3. Detailed Implementation Plan

### A. The 3-Layer Context Storage

Zhora organizes data in three distinct layers to enable fast retrieval:

1. **Layer 1 (Raw):** Stores the original `.mp4`, `.pdf`, and `.csv` files in a local `/storage/raw/` directory.
    
2. **Layer 2 (Context):** FastAPI background tasks extract video frames (e.g., 1 frame every 5 seconds) and text snippets. GPT-4o analyzes these to create small JSON context files (e.g., `"scaffolding issues detected at 01:22"`).
    
3. **Layer 3 (Generalization):** Summaries of Layer 2 data are converted into vector embeddings and stored in **SQLite** using the `sqlite-vec` extension for semantic search.
    

### B. Google Integration

Instead of external automation, Zhora uses a simple **Sync Loop** in Python:

- **Authentication:** Set up a Google Cloud Project and use the `google-auth-oauthlib` to obtain user consent.
    
- **Polling Script:** A FastAPI background task runs every 10 minutes to:
    
    - Search Gmail for attachments or keywords related to "Project A".
        
    - List new files in a designated Google Drive folder.
        
    - Download new items directly to the local Layer 1 storage.
        

### C. The Aegis "Eyes" Tab

- **Video Playback:** Next.js streams videos directly from the local disk via a FastAPI streaming route.
    
- **AI Scrubbing:** When a user asks "Show me the unsafe behavior," Zhora searches the **SQLite** vector index to find the exact timestamp from Layer 2 and tells the video player to jump to that moment.
    

---

## 4. Operational Workflow: "Ask, Don't Configure"

1. **User Ingests:** Connects Google account or drags a file into Next.js.
    
2. **Zhora Processes:** FastAPI saves the file locally and triggers an AI analysis task in the background.
    
3. **Zhora Understands:** GPT-4o populates Layer 2 (context) and Layer 3 (general summaries).
    
4. **User Queries:** "Summarize concrete issues." Zhora searches Layer 3 in SQLite and generates a plain-English report with video clip links from Aegis.
    