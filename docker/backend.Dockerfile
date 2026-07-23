# Backend (FastAPI) — deployed to Azure Container Apps (Chunk 10)
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# WeasyPrint native dependencies for server-side PDF rendering (Chunk 8)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -g app app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# In-process MCP fallback needs the server package + framework data available:
COPY mcp-server/app /mcp-server/app
COPY frameworks /frameworks

RUN mkdir -p /app/data && chown -R app:app /app /mcp-server /frameworks
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request as u,sys; u.urlopen('http://127.0.0.1:8000/api/health'); " || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
