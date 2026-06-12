FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command for the web app
CMD ["uvicorn", "eagle_gallery_app:app", "--host", "0.0.0.0", "--port", "34920"]
