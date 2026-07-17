import re

with open("backend/main.py", "r") as f:
    content = f.read()

# 1. Add imports for slowapi, secure, and fastapi_cache
imports_to_add = """
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from secure import Secure
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from fastapi import Request
"""

content = content.replace("from fastapi.middleware.cors import CORSMiddleware", "from fastapi.middleware.cors import CORSMiddleware\n" + imports_to_add)

# 2. Setup Limiter and Secure
setup_code = """
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

secure_headers = Secure()
@app.middleware("http")
async def set_secure_headers(request, call_next):
    response = await call_next(request)
    secure_headers.framework.fastapi(response)
    return response
"""
content = content.replace("app.add_middleware(", setup_code + "\napp.add_middleware(")

# 3. Add Startup event for Cache
startup_code = """
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
"""
content = content.replace("database.init_db()", "database.init_db()\n" + startup_code)

# 4. Add /health
health_endpoint = """
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}
"""
content = content.replace("@app.get(\"/\")", health_endpoint + "\n@app.get(\"/\")")

# 5. Add rate limit to trigger
content = content.replace(
    "def trigger_disaster(req: DisasterTriggerRequest):",
    "def trigger_disaster(request: Request, req: DisasterTriggerRequest):"
)
content = content.replace(
    "@app.post(\"/api/disaster/trigger\", response_model=SituationReport)",
    "@app.post(\"/api/disaster/trigger\", response_model=SituationReport)\n@limiter.limit(\"10/minute\")"
)

# 6. Add cache to /api/state and /api/incidents
content = content.replace(
    "@app.get(\"/api/state\")",
    "@app.get(\"/api/state\")\n@cache(expire=10)"
)
content = content.replace(
    "@app.get(\"/api/incidents\")",
    "@app.get(\"/api/incidents\")\n@cache(expire=30)"
)

with open("backend/main.py", "w") as f:
    f.write(content)
