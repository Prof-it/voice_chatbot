FROM python:3.11-slim

# 🛠 Install ffmpeg and required system tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg2 && \
    echo "deb http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian bullseye-updates main" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 📁 Set working directory
WORKDIR /app

# 📦 Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 🔄 Copy the rest of the source code
COPY . .

# 🔧 Set environment variables
ENV PYTHONPATH=/app


# 🚀 Start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
