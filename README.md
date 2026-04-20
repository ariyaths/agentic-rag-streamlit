# Intelligent Agentic RAG System

Welcome to the Intelligent Streamlit Agentic Retrieval-Augmented Generation (RAG) System. This application enables you to ingest your custom documents (PDFs, Markdown, and Text files) and interactively question an AI agent that is restricted to synthesizing answers based *only* on the provided context.

## 🖥️ What to Expect on Launch

When you run the application using `streamlit run app.py`, your browser will open to a dashboard interface featuring a **sidebar** on the left and **four primary tabs** in the main viewing area.

### 1. The Sidebar
Here you must provide your authentication credentials.
* **API Key Field:** Enter your **Google Gemini API Key** (this is treated as a secure password field). 

### 2. Tab 1: 📂 Data Setup
This is where the data ingestion process begins.
* **"Load Documents" Button:** Instructs the app to read all `.txt`, `.md`, and `.pdf` files located in your local `/data` directory. 
* **Summary Table:** After loading, you will see a detailed summary table parsing file names, page/section counts, and total word counts.

### 3. Tab 2: ✂️ Chunking & Embedding
This tab controls how your documents are split into manageable pieces for the AI.
* **Configuration Sliders:** Select your splitting strategy (Recursive or Paragraph) and adjust the chunk sizes.
* **"Apply Chunking" Button:** Slices the loaded documents.
* **"Build Vector Store" Button:** Crucial step. This converts text chunks to numerical embeddings using Gemini and saves them to a local FAISS database so the Agent can search them.

### 4. Tab 3: 💬 Agentic RAG Interface
This is the primary chat interface where you interact with the agent.
* **Query Input:** A text box for your question. 
* **Dynamic Response Area:** Shows the AI's response, highlights if "Guardrails" (safety checks) passed, and explicitly tells you *which* internal tool the agent autonomously selected to best answer your prompt.

### 5. Tab 4: 🛡️ Logs & Safety Monitor
An analytical dashboard for auditing.
* Includes a history DataFrame tracking timestamps, query content, duration latency, security guardrail triggers, and which specialized tool handled the request.

---

## 🚦 Navigation Workflow (How to use it)

To successfully query the agent, follow these sequential steps:

1. **Prepare Data:** Create a folder named `data` in the same directory as the app and put your PDFs or text files inside it.
2. **Authenticate:** Enter your Google Gemini API Key into the left sidebar.
3. **Load:** Go to **Tab 1** and click "Load Documents". Wait for the success metric to appear.
4. **Chunk & Embed:** Go to **Tab 2**. Choose your preferred chunk settings and click "Apply Chunking." **Next, you MUST click "Build Vector Store"**. Wait until you see the success message confirming the FAISS index is built.
5. **Chat:** Navigate to **Tab 3**. Type your question and click submit. 
   * *Pro-tip: Try referencing specific files (e.g., "What are the rules file: employee_handbook.pdf") or demanding depth (e.g., "Explain carefully...") to see the agent activate different tools!*

---

## ✅ DOs and ❌ DON'Ts

### ✅ Do:
* **DO** ensure your API key has access to both `gemini-2.5-flash` and `models/gemini-embeddings-001`.
* **DO** rebuild the vector store (in Tab 2) if you add new files into the `data` folder. The RAG will only know about documents present during the active FAISS build.
* **DO** regularly check **Tab 4 (Logs)** to monitor for blocked queries if your prompt triggers the system's guardrails.
* **DO** experiment with system keywords. Asking the system to explain something "detailed", "carefully", or "thoroughly" triggers a hidden Elaborator Tool that rewrites your prompt for higher quality results.

### ❌ Don't:
* **DON'T** start asking questions in Tab 3 before clicking "Build Vector Store" in Tab 2. The system doesn't have a searchable brain until you complete the embedding phase.
* **DON'T** put non-text files (like images or executables) in the `data/` folder, as the built-in PyPDFLoader and TextLoader cannot process them.
* **DON'T** share your `faiss_index` folder publicly if your scanned PDFs contained sensitive data. The index can be reverse-engineered to extract the original text.

## 🛠️ Tool Flow Description (Under the Hood)

The Agentic Router implements advanced query preprocessing to enhance accuracy and reduce hallucinations before your query even reaches the vector store:

### 1. Strict Document Filtering via Regex Matching
The system uses regular expressions (Regex) to parse your input for specific citation commands like `file:` or `from`. 
When the user query explicitly demands information from a targeted source (e.g., *"What is our policy from employee_handbook.pdf?"*), the routing engine isolates the requested filename. The FAISS vector database search is then selectively filtered to *only* return chunks carrying that exact `source` metadata. By restricting the context window exclusively to the indicated document, the chance of the LLM suffering from "cross-contamination" or hallucinating facts from unrelated documents is drastically reduced.

### 2. Prompt Re-engineering via Adverb Detection
If the agent router detects analytical adverbs in your prompt—such as `thoroughly`, `detailed`, `carefully`, or `deeply`—it recognizes an intent for high-quality, comprehensive analysis. 
Instead of sending your raw question directly to the vector search, the system redirects your query to a **Prompt Re-engineering LLM Chain** (the "Elaborator Tool"). This initial LLM pass rewrites and expands your original query into a highly optimized, multi-faceted search prompt. This re-engineered prompt is then routed to the FAISS vector database, guaranteeing that the context chunks ultimately retrieved are much richer and more deeply relevant to producing a "thorough" final response.

## 💡 Challenges & Key Learnings

### Standardizing Multi-Format Metadata
One of the primary challenges encountered was securely tracking and matching metadata across vastly different file types. For example, `PyPDFLoader` automatically extracts and attaches complex dictionary objects to PDF chunks (including page numbers, authors, and absolute system paths), whereas `TextLoader` handles plain text differently and sometimes omits default properties entirely. 

If the metadata structures were left inconsistent between PDFs and TXT files, the Regex filtering in the Agent Router would fail to match the source file reliably, causing search errors or leaked context.

**The Solution:** This hurdle was overcome by artificially standardizing the metadata extraction during the initial ingestion loop in `app.py`. Regardless of the source loader used, the script actively writes and standardizes the `metadata["source"]` field to be exactly the clean file name (e.g., `employee_handbook.pdf` or `notes.txt`) and sets uniform baseline attributes. This guarantees the LLM tools always have a predictable schema to query against.

```mermaid
flowchart TD
    %% Define styles
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef user fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef streamlit fill:#ffe0b2,stroke:#f57c00,stroke-width:2px;
    classDef google fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef storage fill:#ede7f6,stroke:#512da8,stroke-width:2px;
    classDef security fill:#ffebee,stroke:#d32f2f,stroke-width:2px;
    
    User((User)):::user
    
    subgraph UI ["Streamlit Frontend (app.py)"]
        UI_Docs["Document Setup Tab"]:::streamlit
        UI_Chunk["Embeddings Tab"]:::streamlit
        UI_Chat["Chat Interface Tab"]:::streamlit
        UI_Logs["System Logs Tab"]:::streamlit
    end

    subgraph Data_Processing ["Data Ingestion"]
        DocLoaders["Document Loaders<br>(PyPDF, TextLoader)"]
        Splitters["Text Splitters"]
    end
    
    subgraph VectorDB ["FAISS Store"]
        CacheCheck{"Cache Metadata<br>Match?"}
        FAISSSave[("Save faiss_index")]:::storage
        FAISSLoad[("Load faiss_index")]:::storage
    end

    subgraph External_NLP ["Google Generative AI"]
        EmbeddingAPI["Embedding API<br>(text-embedding-004)"]:::google
        LLM["Generative Model API<br>(gemini-1.5-flash)"]:::google
    end

    subgraph Middlewares ["Security & Routing"]
        GuardIn{"Input Guardrail<br>(Regex check)"}:::security
        Agent["Agent Router<br>(agent_tools.py)"]
        GuardOut{"Output Guardrail<br>(Regex check)"}:::security
    end

    %% Data Ingestion Flow
    User -->|"Load Files"| UI_Docs
    UI_Docs --> DocLoaders
    DocLoaders --> Splitters
    Splitters --> UI_Chunk
    UI_Chunk -->|"Build Vector Store"| CacheCheck
    
    CacheCheck -->|"No (New Docs/Params)"| EmbeddingAPI
    EmbeddingAPI --> FAISSSave
    
    CacheCheck -->|"Yes (Exact Match)"| FAISSLoad

    %% Query Flow
    User -->|"Ask Question"| UI_Chat
    UI_Chat --> GuardIn
    
    GuardIn -->|"Fails"| BlockIn["Block & Log"]:::security
    GuardIn -->|"Passes"| Agent
    
    %% RAG logic
    FAISSLoad -.->|"Search Relevant Chunks"| Agent
    FAISSSave -.->|"Search Relevant Chunks"| Agent
    
    %% Agent & LLM Communication (Fixed Bi-directional)
    Agent -->|"Context & Query"| LLM
    LLM -->|"Generated Response"| Agent
    v
    %% Output Flow
    Agent --> GuardOut
    GuardOut -->|"Fails"| BlockOut["Block & Log"]:::security
    GuardOut -->|"Passes"| FinalOutput["Display Answer"]
    
    BlockIn --> UI_Logs
    BlockOut --> UI_Logs
    FinalOutput --> UI_Chat
```
