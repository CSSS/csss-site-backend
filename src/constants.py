import os

root_ip_address = "http://localhost:8000" if os.environ.get("LOCAL") == "true" else "https://api.sfucsss.org"
