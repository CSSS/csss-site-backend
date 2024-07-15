import os

root_ip_address = "http://localhost:8000" if os.environ.get("LOCAL") == "true" else "https://api.sfucsss.org"
guild_id = "1260652618875797504" if os.environ.get("LOCAL") == "true" else "228761314644852736"
