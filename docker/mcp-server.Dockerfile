# MCP Server — deployed to Azure Container Apps (Chunk 10)
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MCP_PORT=8100 MCP_HOST=0.0.0.0
WORKDIR /app

# Non-root runtime user (least privilege)
RUN groupadd -r app && useradd -r -g app app

COPY mcp-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp-server/app ./app
# Framework data is mounted read-only in compose; baked in for the image build:
COPY frameworks /app/frameworks

USER app
EXPOSE 8100
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0)"
# Streamable HTTP transport for network access from the backend
CMD ["uvicorn", "app.http:app", "--host", "0.0.0.0", "--port", "8100"]
