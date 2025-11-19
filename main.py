from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import pdfplumber
import docx
import tempfile
import os
import re
import subprocess

app = FastAPI(title="File Parser Microservice")

def parse_pdf(file_path):
    text = ""

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

            # Include hyperlinks in the text
            if page.hyperlinks:
                for h in page.hyperlinks:
                    if "uri" in h:
                        uri = h["uri"]
                        # Append hyperlink to the text
                        text += f" [{uri}]\n"

    return text

def parse_docx(file_path):
    document = docx.Document(file_path)
    text_parts = []

    # Extract text and hyperlinks from paragraphs
    for p in document.paragraphs:
        para_text = p.text
        text_parts.append(para_text)
        
        # Check paragraph XML for hyperlink elements and include them in text
        if p._element.xml:
            # Find hyperlink relationship IDs in paragraph XML
            rel_ids = re.findall(r'<w:hyperlink[^>]*r:id="([^"]*)"', p._element.xml)
            for rel_id in rel_ids:
                if rel_id in document.part.rels:
                    rel = document.part.rels[rel_id]
                    # Get the target URL from the relationship
                    try:
                        # Try different ways to access the target
                        target = None
                        if hasattr(rel, 'target'):
                            target = rel.target
                        elif hasattr(rel, '_target'):
                            target = rel._target
                        elif hasattr(rel, 'target_ref'):
                            target = rel.target_ref
                        
                        if target:
                            # Include hyperlink in the text
                            if isinstance(target, str) and (target.startswith('http') or target.startswith('mailto:')):
                                text_parts.append(f" [{target}]")
                    except Exception:
                        # Skip if we can't extract the target
                        pass

    return "\n".join(text_parts)

def parse_doc(file_path):
    try:
        import textract
        # Extract text from .doc file using textract
        text = textract.process(file_path).decode('utf-8')
        
        # Note: .doc files (binary format) don't preserve hyperlink information easily
        # Textract extracts plain text only, hyperlinks are typically lost in .doc format
        # If hyperlink extraction is critical for .doc files, consider converting to .docx first
        
        return text
    except ImportError:
        # Fallback: try using antiword via subprocess if textract is not available
        try:
            result = subprocess.run(
                ['antiword', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
            else:
                raise Exception("Failed to extract text from .doc file")
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            raise Exception(f"Could not parse .doc file. Please ensure textract or antiword is installed. Error: {str(e)}")

@app.post("/parse-file")
async def parse_file(file: UploadFile = File(...)):
    ext = file.filename.lower().split(".")[-1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        if ext == "pdf":
            text = parse_pdf(tmp_path)
        elif ext == "docx":
            text = parse_docx(tmp_path)
        elif ext == "doc":
            text = parse_doc(tmp_path)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported file type: {ext}"},
            )

        return {
            "filename": file.filename,
            "text": text.strip(),
        }

    finally:
        os.remove(tmp_path)
