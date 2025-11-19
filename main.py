from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import pdfplumber
import mammoth
import docx
import tempfile
import os

app = FastAPI(title="File Parser Microservice")

def parse_pdf(file_path):
    text = ""
    links = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

            if page.hyperlinks:
                for h in page.hyperlinks:
                    if "uri" in h:
                        links.append(h["uri"])

    return text, list(set(links))

def parse_docx(file_path):
    document = docx.Document(file_path)
    text = []
    links = []

    for p in document.paragraphs:
        text.append(p.text)
        for r in p.runs:
            if r.hyperlink:
                links.append(r.hyperlink.target)

    return "\n".join(text), list(set(links))

def parse_doc(file_path):
    with open(file_path, "rb") as f:
        result = mammoth.convert_to_html(f)

    html = result.value

    import re
    links = re.findall(r'href="(.*?)"', html)
    text = re.sub(r"<[^>]+>", "", html)

    return text, list(set(links))

@app.post("/parse-file")
async def parse_file(file: UploadFile = File(...)):
    ext = file.filename.lower().split(".")[-1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        if ext == "pdf":
            text, links = parse_pdf(tmp_path)
        elif ext == "docx":
            text, links = parse_docx(tmp_path)
        elif ext == "doc":
            text, links = parse_doc(tmp_path)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported file type: {ext}"},
            )

        return {
            "filename": file.filename,
            "text": text.strip(),
            "hyperlinks": links,
        }

    finally:
        os.remove(tmp_path)
