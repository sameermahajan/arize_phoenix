from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor
from openai import OpenAI
from opentelemetry import trace

# Register Phoenix OTEL exporter
tracer_provider = register()

# Auto-instrument OpenAI-compatible clients
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

# Connect to Ollama
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("ollama-workflow"):
    response = client.chat.completions.create(
        model="llama3.1",
        messages=[{"role": "user", "content": "Explain tracing briefly."}],
    )

print(response.choices[0].message.content)