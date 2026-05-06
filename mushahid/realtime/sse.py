# TODO: Mushahid — SSE streaming helpers.
# format_event(event_name: str, data: dict) → str
#   Format as SSE: "event: {name}\ndata: {json}\n\n"
# stream_pipeline_events(generator) → StreamingResponse
#   Wrap an async generator of SSE strings into a FastAPI StreamingResponse
#   with content-type text/event-stream.
