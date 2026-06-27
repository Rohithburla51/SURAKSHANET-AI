FROM python:3.10-slim

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

EXPOSE 7860

# Run from backend directory
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--app-dir", "/app/backend"]
