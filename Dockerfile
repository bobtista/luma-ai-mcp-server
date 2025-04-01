FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies using uv
RUN uv venv .venv
RUN . .venv/bin/activate && uv pip install -e .

# Run the server
CMD ["python", "-m", "luma-ai-mcp-server"] 