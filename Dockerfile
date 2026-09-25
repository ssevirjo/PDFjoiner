FROM python:3.12-slim

# Install system dependencies: LibreOffice for Word/DOCX conversion on Linux,
# plus Unicode Baltic/European fonts for perfect Latvian diacritics rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-calc \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications
COPY requirements.txt .

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Render.com provides $PORT dynamically (defaults to 3335 locally)
ENV PORT=3335
EXPOSE 3335

# Start FastAPI server using uvicorn
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-3335}"]
