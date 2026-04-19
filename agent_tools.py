import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

def get_llm(api_key: str = None):
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=api_key)

def rag_retriever_tool(query: str, vector_store, api_key: str = None):
    """Standard RAG retrieval and generation."""
    llm = get_llm(api_key)
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
    
    prompt = ChatPromptTemplate.from_template(
        "Answer the question based only on the provided context:\n\n{context}\n\nQuestion: {input}"
    )
    
    document_chain = create_stuff_documents_chain(llm, prompt)
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    response = retrieval_chain.invoke({"input": query})
    return response["answer"]

def filter_tool(query: str, vector_store, filename: str, api_key: str = None):
    """Filters chunks using file-based metadata before passing to the LLM."""
    llm = get_llm(api_key)
    
    # Fetch a larger pool of documents to filter manually by source
    docs = vector_store.similarity_search(query, k=15)
    filtered_docs = [d for d in docs if filename.lower() in str(d.metadata.get("source", "")).lower()]
    
    if not filtered_docs:
        return f"No documents found matching the file filter: '{filename}'."
        
    prompt = ChatPromptTemplate.from_template(
        "Answer the question based only on the provided context from the specified file:\n\n{context}\n\nQuestion: {input}"
    )
    
    document_chain = create_stuff_documents_chain(llm, prompt)
    response = document_chain.invoke({"context": filtered_docs[:4], "input": query})
    return response

def elaborator_tool(query: str, vector_store, api_key: str = None):
    """Expands vague user queries by rephrasing before the RAG call."""
    llm = get_llm(api_key)
    prompt = ChatPromptTemplate.from_template(
        "You are an AI assistant. The user asked a vague query. Rewrite and expand it into a detailed, comprehensive search query. Return ONLY the expanded query.\n\nOriginal query: {query}"
    )
    expanded_query = llm.invoke(prompt.format_messages(query=query)).content
    
    # Send expanded query back to standard RAG pipeline
    answer = rag_retriever_tool(expanded_query, vector_store, api_key)
    return answer, expanded_query

def agent_router(query: str, vector_store, api_key: str = None):
    """Inspects the query and dynamically routes to the correct tool."""
    query_lower = query.lower()
    
    # Tool 1: Filter Tool (Triggers on 'file: filename.pdf' or 'from filename.md')
    match = re.search(r'(?:file:|from)\s*([\w.-]+)', query_lower)
    if match:
        filename = match.group(1)
        return "Filter Tool", filter_tool(query, vector_store, filename, api_key), f"Filtered specifically for: '{filename}'"
        
    # Tool 2: Elaborator Tool (Triggers on specific keywords)
    if any(word in query_lower for word in ["carefully", "detailed", "thoroughly"]):
        answer, expanded = elaborator_tool(query, vector_store, api_key)
        return "Elaborator Tool", answer, f"Expanded query to: '{expanded}'"
        
    # Tool 3: Standard RAG (Default fallback)
    return "RAG Retriever Tool", rag_retriever_tool(query, vector_store, api_key), "Standard semantic search applied."