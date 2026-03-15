# start phoenix UI

phoenix serve

# run program

python main.py

# lookup traces

http://localhost:6006/

# AX Free

app.arize.com

set ARIZE_API_KEY and ARIZE_SPACE_ID

tracer_provider = register(
    project_name="<your project name>",  
    endpoint="https://otlp.arize.com/v1/traces",
    protocol="http/protobuf",  # Explicitly set protocol
    headers={
        "api_key": os.getenv("ARIZE_API_KEY"),
        "space_id": os.getenv("ARIZE_SPACE_ID"),
    },)
