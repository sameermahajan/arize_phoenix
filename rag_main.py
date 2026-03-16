from dotenv import load_dotenv
import os

load_dotenv()

# -----------------------------
# Phoenix tracing
# -----------------------------
from phoenix.otel import register

tp = register(
    project_name="ollama-openai-rag",
    endpoint="https://otlp.arize.com/v1/traces",
    protocol="http/protobuf",  # Explicitly set protocol
    headers={
        "api_key": os.getenv("ARIZE_API_KEY"),
        "space_id": os.getenv("ARIZE_SPACE_ID"),
    },
)

# -----------------------------
# Instrument OpenAI
# -----------------------------
from openinference.instrumentation.openai import OpenAIInstrumentor
OpenAIInstrumentor().instrument()

# -----------------------------
# OpenAI client → Ollama
# -----------------------------
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

# -----------------------------
# Vector DB
# -----------------------------
import chromadb

chroma_client = chromadb.Client()
collection = chroma_client.create_collection("rag-demo")

docs = [
    "Arize Phoenix is an open-source observability tool for LLM applications.",
    "RAG stands for Retrieval Augmented Generation.",
    "Vector databases store embeddings for semantic search.",
    "Ollama allows running LLMs locally."
]

# -----------------------------
# Create embeddings
# -----------------------------
for i, doc in enumerate(docs):

    emb = client.embeddings.create(
        model="nomic-embed-text",
        input=doc
    )

    collection.add(
        documents=[doc],
        embeddings=[emb.data[0].embedding],
        ids=[str(i)]
    )

# -----------------------------
# User query
# -----------------------------
query = "What is Arize Phoenix?"

print("\nUser Query:")
print(query)

# -----------------------------
# Query embedding
# -----------------------------
query_emb = client.embeddings.create(
    model="nomic-embed-text",
    input=query
)

# -----------------------------
# Vector search
# -----------------------------
results = collection.query(
    query_embeddings=[query_emb.data[0].embedding],
    n_results=2
)

retrieved_docs = results["documents"][0]

print("\nRetrieved Context:")
for d in retrieved_docs:
    print("-", d)

# -----------------------------
# Build prompt
# -----------------------------
context = "\n".join(retrieved_docs)

prompt = f"""
Answer the question using the context.

Context:
{context}

Question:
{query}
"""

# -----------------------------
# LLM call (OpenAI API → Ollama)
# -----------------------------
response = client.chat.completions.create(
    model="llama3.1",
    messages=[
        {"role": "user", "content": prompt}
    ]
)

print("\nLLM Response:")
print(response.choices[0].message.content)

# -----------------------------
# Flush traces
# -----------------------------
tp.force_flush()