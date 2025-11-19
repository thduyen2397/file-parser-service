# File Parser Microservice

Parses PDF, DOC, DOCX for text + hyperlinks.

## Run locally
uvicorn main:app --reload --host 0.0.0.0 --port 8080

## Run in Docker
docker build -t file-parser .
docker run -p 8080:8080 file-parser

## Run with docker-compose
docker-compose up --build

## API Endpoint
POST /parse-file
Form-data:
- file: (binary file)

Returns JSON:
{
  "filename": "...",
  "text": "...",
  "hyperlinks": [...]
}
