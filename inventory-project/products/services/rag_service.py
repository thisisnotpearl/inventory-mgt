"""
Retrieval-Augmented Generation (RAG) Service

This service handles the "Ask the Expert" chatbot functionality.
It uses LangChain to:
1. Load text documents (Manuals, Policies, FAQs)
2. Split them into manageable chunks
3. Convert them into vectors using sentence-transformers
4. Store them in a local ChromaDB vector database
5. Retrieve the most relevant chunks when a user asks a question
6. Pass the chunks + the user's question to Groq (Llama 3) to generate an answer
"""

import os
import glob
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Path to the ChromaDB storage directory (created locally)
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class RAGService:
    _vectorstore = None

    @staticmethod
    def _get_vectorstore():
        """Initialize and cache the ChromaDB connection."""
        if RAGService._vectorstore is None:
            # We use the same embedding model as Week 7 for consistency
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
            # Connect to the local ChromaDB database
            RAGService._vectorstore = Chroma(
                persist_directory=CHROMA_DB_DIR,
                embedding_function=embeddings
            )
        return RAGService._vectorstore

    @staticmethod
    def ingest_documents():
        """
        Load all text files from the data directory, split them into chunks,
        and store them in ChromaDB. This is the "R" in RAG (Retrieval setup).
        """
        # 1. Find all .txt files in the data directory
        txt_files = glob.glob(os.path.join(DATA_DIR, "*.txt"))
        if not txt_files:
            raise FileNotFoundError("No .txt documents found in products/data/")

        # 2. Load the text from the files
        docs = []
        for file_path in txt_files:
            loader = TextLoader(file_path, encoding='utf-8')
            docs.extend(loader.load())

        # 3. Chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        chunks = text_splitter.split_documents(docs)

        # 4. Embed and Store in ChromaDB
        # On Windows, using shutil.rmtree() causes a "File in use" error 
        # because the Django process holds a lock on the ChromaDB files.
        # Instead, we tell ChromaDB to natively delete its own collection.
        vectorstore = RAGService._get_vectorstore()
        try:
            vectorstore.delete_collection()
        except Exception:
            pass
        RAGService._vectorstore = None

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        RAGService._vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DB_DIR
        )

        return {"status": "success", "chunks_ingested": len(chunks)}

    @staticmethod
    def retrieve_relevant_chunks(query: str, top_k: int = 3):
        """
        Search the vector database for chunks related to the user's query.
        Returns the raw text chunks (useful for evaluation and debugging).
        """
        vectorstore = RAGService._get_vectorstore()
        
        # as_retriever allows LangChain to use this DB as a search engine
        retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
        
        # Execute the search
        docs = retriever.invoke(query)
        
        return [{"content": d.page_content, "source": d.metadata.get("source", "unknown")} for d in docs]

    @staticmethod
    def ask_expert(query: str):
        """
        The full RAG pipeline: Query -> Retrieve Chunks -> Prompt LLM -> Return Answer.
        """
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not found in environment.")

        # 1. Setup the Retriever
        vectorstore = RAGService._get_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        # 2. Setup the LLM
        llm = ChatGroq(
            api_key=api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1  # Keep temperature low to prevent hallucinations
        )

        # 3. Create the "Grounded" Prompt
        # This forces the AI to ONLY use the retrieved chunks, preventing hallucinations.
        template = """You are a helpful expert assistant for the Toy Store.
Use ONLY the following pieces of retrieved context to answer the user's question.
If the answer is not contained in the context, say exactly: "I don't have enough information to answer that."
Do not make up information.

Context:
{context}

Question: {question}

Answer:"""
        prompt = ChatPromptTemplate.from_template(template)

        # 4. Build the LangChain
        # This pipe (|) syntax automatically passes the output of one step to the input of the next.
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        # 5. Execute the chain
        # If LangSmith environment variables are set in .env, this invocation
        # is automatically traced and logged to the LangSmith dashboard!
        answer = rag_chain.invoke(query)

        # Also retrieve the source chunks to show the user *why* it answered that way
        sources = RAGService.retrieve_relevant_chunks(query)

        return {
            "answer": answer,
            "sources": sources
        }

    # ── Advanced: Combined DB + RAG ────────────────────────────────────

    @staticmethod
    def ask_expert_with_stock(query: str):
        """
        ADVANCED: Combines RAG (document retrieval) with a live Database query.
        If a user asks "Do we have the Lego Castle in stock, and what is its warranty?",
        this function retrieves the warranty from ChromaDB and the stock from MongoDB.
        """
        from products.services.embedding_service import EmbeddingService
        
        # 1. RAG Retrieval (Get the Warranty/Manual info)
        vectorstore = RAGService._get_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        rag_docs = retriever.invoke(query)
        rag_context = "\n\n".join(doc.page_content for doc in rag_docs)

        # 2. Database Retrieval (Get live stock levels)
        # We use our Week 7 Semantic Search to find the most relevant products!
        db_context = ""
        matched_products = []
        
        try:
            # Get top 5 most semantically related products from MongoDB
            # We explicitly lower the threshold so broader questions like 
            # "do we have any electronics" still find items.
            similar_products = EmbeddingService.semantic_search(query, top_k=5, threshold=0.10)
            
            for p in similar_products:
                matched_products.append(p["name"])
                db_context += f"- {p['name']} (Brand: {p.get('brand', 'Unknown')}): {p.get('quantity', 0)} units in stock. Price: ₹{p.get('price', 0)}\n"
        except Exception as e:
            db_context = f"Error retrieving database context: {e}"

        if not db_context:
            db_context = "No specific database records matched the query."

        # 3. Setup the LLM & Prompt
        api_key = os.getenv("GROQ_API_KEY")
        llm = ChatGroq(api_key=api_key, model_name="llama-3.3-70b-versatile", temperature=0.1)

        template = """You are a helpful expert assistant for the Toy Store.
You have access to two sources of information:
1. Documentation Context (Manuals, Policies):
{rag_context}

2. Live Database Context (Current Stock & Prices):
{db_context}

Answer the user's question using ONLY the provided context. 
If the answer requires stock info, use the Database Context.
If the answer requires policy/manual info, use the Documentation Context.
If the context doesn't contain the answer, say "I don't have enough information to answer that."

Question: {question}

Answer:"""
        prompt = ChatPromptTemplate.from_template(template)

        # 4. Build and Execute Chain
        chain = prompt | llm | StrOutputParser()
        
        answer = chain.invoke({
            "rag_context": rag_context,
            "db_context": db_context,
            "question": query
        })

        return {
            "answer": answer,
            "sources": [{"content": d.page_content} for d in rag_docs],
            "db_hits": matched_products
        }
