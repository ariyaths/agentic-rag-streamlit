import streamlit as st
import os
import time
import json
import pandas as pd
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

from agent_tools import agent_router
from guardrails import check_guardrails, get_guardrail_message

load_dotenv()

st.set_page_config(page_title="Agentic RAG System", layout="wide")
st.title("🤖 Intelligent Agentic RAG System")

# State Initialization
if "documents" not in st.session_state: st.session_state.documents = []
if "chunks" not in st.session_state: st.session_state.chunks = []
if "vector_store" not in st.session_state: st.session_state.vector_store = None
if "logs" not in st.session_state: st.session_state.logs = []

api_key_input = st.sidebar.text_input("Google Gemini API Key (Optional if in .env):", type="password")
api_key = api_key_input or os.getenv("GOOGLE_API_KEY", "")

if api_key:
    # Do not set global os.environ to prevent multi-user leakage
    st.session_state.gemini_key = api_key

# 4 UI Tabs Required by Rubric
tab1, tab2, tab3, tab4 = st.tabs(["📂 Data Setup", "✂️ Chunking & Embedding", "💬 Agentic RAG Interface", "🛡️ Logs & Safety Monitor"])

# --- TAB 1: DATA SETUP ---
with tab1:
    st.header("1. Load & Preprocess Documents")
    if st.button("Load Documents from /data"):
        data_dir = "data"
        if not os.path.exists(data_dir):
            st.error(f"Directory '{data_dir}' not found.")
        else:
            docs = []
            # Identify files already processed in this session
            processed_files = {doc.metadata.get("source") for doc in st.session_state.documents}
            new_files_count = 0
            
            for file in os.listdir(data_dir):
                if file in processed_files:
                    continue  # Skip files we already possess
                    
                path = os.path.join(data_dir, file)
                try:
                    if file.endswith(".pdf"):
                        loader = PyPDFLoader(path)
                        for i, page in enumerate(loader.load()):
                            page.metadata.update({"source": file, "page": i + 1, "author": "Extracted"})
                            docs.append(page)
                        new_files_count += 1
                    elif file.endswith((".txt", ".md")):
                        loader = TextLoader(path, encoding="utf-8")
                        for page in loader.load():
                            page.metadata.update({"source": file, "page": 1, "author": "Extracted"})
                            docs.append(page)
                        new_files_count += 1
                except Exception as e:
                    st.warning(f"Error loading {file}: {e}")
            
            # Append new docs instead of overwriting the session state
            st.session_state.documents.extend(docs)
            st.success(f"Successfully loaded {new_files_count} newly added files ({len(docs)} new pages/sections).")
            
    if st.session_state.documents:
        st.subheader("Loaded Files Summary")
        summary = {}
        for doc in st.session_state.documents:
            src = doc.metadata.get("source", "Unknown")
            word_count = len(doc.page_content.split())
            if src in summary:
                summary[src]["Total Words"] += word_count
                summary[src]["Pages/Sections"] += 1
            else:
                summary[src] = {"File Name": src, "Total Words": word_count, "Pages/Sections": 1}
        st.table(pd.DataFrame(summary.values()))

# --- TAB 2: CHUNKING & EMBEDDING ---
with tab2:
    st.header("2. Chunking Configuration")
    col1, col2 = st.columns(2)
    with col1:
        strategy = st.selectbox("Chunking Strategy", ["Recursive", "Paragraph", "Fixed-size"])
    with col2:
        chunk_size = st.slider("Chunk Size", 100, 2000, 500)
        chunk_overlap = st.slider("Chunk Overlap", 0, 500, 50)
        
    if st.button("Apply Chunking"):
        if not st.session_state.documents:
            st.warning("Please load documents first.")
        else:
            if strategy == "Recursive":
                splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            elif strategy == "Paragraph":
                splitter = CharacterTextSplitter(separator="\n\n", chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            else:
                splitter = CharacterTextSplitter(separator="", chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                
            st.session_state.chunks = splitter.split_documents(st.session_state.documents)
            for i, chunk in enumerate(st.session_state.chunks):
                chunk.metadata["chunk_id"] = i
            st.success(f"Created {len(st.session_state.chunks)} chunks!")
            
    if st.session_state.chunks:
        with st.expander("Preview Generated Chunks"):
            preview_count = {}
            for chunk in st.session_state.chunks:
                src = chunk.metadata.get("source", "Unknown")
                if preview_count.get(src, 0) < 2:
                    st.write(f"**Metadata:** {chunk.metadata}")
                    st.info(chunk.page_content[:250] + "...")
                    preview_count[src] = preview_count.get(src, 0) + 1

    st.header("3. Embedding & FAISS Indexing")
    if st.button("Build Vector Store"):
            if not st.session_state.chunks or not api_key:
                st.warning("Ensure chunks are generated and Google API key is provided.")
            else:
                with st.spinner("Embedding chunks using Gemini (or loading from disk)..."):
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=api_key)
                    
                    # Define current metadata state
                    current_meta = {
                        "strategy": strategy,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap,
                        "documents": sorted(list({doc.metadata.get("source", "Unknown") for doc in st.session_state.documents}))
                    }
                    
                    meta_path = "faiss_meta.json"
                    index_path = "faiss_index"
                    loaded = False
                    
                    if os.path.exists(meta_path) and os.path.exists(index_path):
                        with open(meta_path, "r") as f:
                            saved_meta = json.load(f)
                        if saved_meta == current_meta:
                            st.session_state.vector_store = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
                            loaded = True
                            
                    if loaded:
                        st.success("Loaded FAISS Vector store from disk! (Zero API calls used)")
                    else:
                        st.session_state.vector_store = FAISS.from_documents(st.session_state.chunks, embeddings)
                        st.session_state.vector_store.save_local(index_path)
                        with open(meta_path, "w") as f:
                            json.dump(current_meta, f)
                        st.success("FAISS Vector store built and persisted!")
                    
                    total_tokens_est = sum(len(c.page_content) // 4 for c in st.session_state.chunks)
                    st.metric("Total Vectors Indexed", len(st.session_state.chunks))
                    st.metric("Estimated Tokens Embedded", total_tokens_est)

# --- TAB 3: AGENTIC RAG INTERFACE ---
with tab3:
    st.header("💬 Query the Agent")
    st.markdown("*Try:* `What is bereavement leave?` | `What are the rules from policy-INPUT-DATA.pdf?` | `Answer carefully about the sonnets.`")
    
    query = st.text_input("Enter your query:")
    if st.button("Submit Query"):
        if not st.session_state.vector_store:
            st.warning("Please build the vector store in Tab 2 first.")
        else:
            start_time = time.time()
            
            # Input Guardrail Pre-Check
            is_safe, triggered_kw = check_guardrails(query)
            if not is_safe:
                st.error(get_guardrail_message(triggered_kw))
                st.session_state.logs.append({"Time": time.strftime("%H:%M:%S"), "Query": query, "Tool": "Blocked (Input)", "Duration (s)": 0, "Guardrail": f"🚨 Triggered ({triggered_kw})"})
            else:
                with st.spinner("Agent routing and reasoning..."):
                    tool_used, response, details = agent_router(query, st.session_state.vector_store, api_key)
                    
                    # Output Guardrail Post-Check
                    out_safe, out_kw = check_guardrails(response, is_input=False)
                    if not out_safe:
                        st.error(get_guardrail_message(out_kw))
                        st.session_state.logs.append({"Time": time.strftime("%H:%M:%S"), "Query": query, "Tool": "Blocked (Output)", "Duration (s)": round(time.time()-start_time, 2), "Guardrail": f"🚨 Triggered ({out_kw})"})
                    else:
                        st.success("Response generated successfully.")
                        st.markdown(f"**Answer:** {response}")
                        st.info(f"🛠️ **Tool Activated:** `{tool_used}` | 📝 **Details:** {details}")
                        st.session_state.logs.append({"Time": time.strftime("%H:%M:%S"), "Query": query, "Tool": tool_used, "Duration (s)": round(time.time()-start_time, 2), "Guardrail": "✅ Passed"})

# --- TAB 4: LOGS & SAFETY MONITOR ---
with tab4:
    st.header("🛡️ System Logs & Monitor")
    if st.session_state.logs:
        st.dataframe(pd.DataFrame(st.session_state.logs), use_container_width=True)
    else:
        st.write("No queries logged yet.")