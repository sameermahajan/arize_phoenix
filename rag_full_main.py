from dotenv import load_dotenv
import os
import chromadb

load_dotenv()

# ---------------------------------------------------
# Phoenix + Arize AX tracing setup
# ---------------------------------------------------
from phoenix.otel import register
from opentelemetry import trace
from openinference.instrumentation.openai import OpenAIInstrumentor

tp = register(
    project_name="ollama-openai-rag-demo",
    endpoint="https://otlp.arize.com/v1/traces",
    protocol="http/protobuf",  # Explicitly set protocol
    headers={
        "api_key": os.getenv("ARIZE_API_KEY"),
        "space_id": os.getenv("ARIZE_SPACE_ID"),
    },
)

OpenAIInstrumentor().instrument()

tracer = trace.get_tracer(__name__)

# ---------------------------------------------------
# OpenAI-compatible client pointing to Ollama
# ---------------------------------------------------
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

# ---------------------------------------------------
# Create VectorDB
# ---------------------------------------------------
chroma_client = chromadb.Client()
collection = chroma_client.create_collection("rag-demo")

documents = [
    "Arize Phoenix is an open-source observability tool for LLM applications.",
    "RAG stands for Retrieval Augmented Generation.",
    "Vector databases store embeddings for semantic search.",
    "Ollama allows running large language models locally.",
]

# ---------------------------------------------------
# Index documents
# ---------------------------------------------------
with tracer.start_as_current_span("index_documents") as span:

    span.set_attribute("rag.num_documents", len(documents))

    for i, doc in enumerate(documents):

        with tracer.start_as_current_span("embedding_document"):

            emb = client.embeddings.create(
                model="nomic-embed-text",
                input=doc
            )

        collection.add(
            documents=[doc],
            embeddings=[emb.data[0].embedding],
            ids=[str(i)]
        )

# ---------------------------------------------------
# User Query
# ---------------------------------------------------
query = "What is Arize Phoenix?"

with tracer.start_as_current_span("user_query") as span:

    span.set_attribute("rag.query", query)

    # ---------------------------------------------------
    # Query embedding
    # ---------------------------------------------------
    with tracer.start_as_current_span("query_embedding"):

        query_embedding = client.embeddings.create(
            model="nomic-embed-text",
            input=query
        )

    # ---------------------------------------------------
    # Vector DB Search
    # ---------------------------------------------------
    with tracer.start_as_current_span("vector_db_search") as span:

        results = collection.query(
            query_embeddings=[query_embedding.data[0].embedding],
            n_results=2,
            include=["documents", "distances"]
        )

        retrieved_docs = results["documents"][0]
        distances = results["distances"][0]

    with tracer.start_as_current_span("vector_db_search") as span:

        span.set_attribute("rag.query", query)
        span.set_attribute("rag.num_results", len(retrieved_docs))

        for i, doc in enumerate(retrieved_docs):

            span.set_attribute(
                f"rag.retrieved_doc_{i}",
                doc[:200]
            )

            span.set_attribute(
                f"rag.distance_{i}",
                float(distances[i])
            )
        # for i, doc in enumerate(retrieved_docs):

        #    span.add_event(
        #        "retrieved_document",
        #        attributes={
        #            "rank": int(i),
        #            "similarity_distance": float(distances[i]),
        #            "content_preview": str(doc[:200]),
        #            "doc_length": int(len(doc)),
        #        }
        #   )
 

    # ---------------------------------------------------
    # Context Assembly
    # ---------------------------------------------------
    with tracer.start_as_current_span("context_assembly") as span:

        context = "\n".join(retrieved_docs)

        span.set_attribute("rag.context_length", len(context))
        span.set_attribute("rag.context_preview", context[:300])

    # ---------------------------------------------------
    # Prompt Construction
    # ---------------------------------------------------
    prompt = f"""
Answer the question using the context below.

Context:
{context}

Question:
{query}
"""

    # ---------------------------------------------------
    # LLM Generation
    # ---------------------------------------------------
    with tracer.start_as_current_span("llm_generation") as span:

        span.set_attribute("llm.model", "llama3.1")
        span.set_attribute("llm.prompt_preview", prompt[:400])

        response = client.chat.completions.create(
            model="llama3.1",
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.choices[0].message.content

        span.set_attribute("llm.response_preview", answer[:300])

print("\nUser Query:")
print(query)

print("\nRetrieved Context:")
for doc in retrieved_docs:
    print("-", doc)

print("\nLLM Response:")
print(answer)

# ---------------------------------------------------
# Flush traces to Arize
# ---------------------------------------------------
tp.force_flush()