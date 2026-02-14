from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os, uuid

from engine.factory import run_parser

app = FastAPI(title="WA Parser API")

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================
# MODEL (UNTUK JSON API)
# ============================
class ParseTextRequest(BaseModel):
    text: str
    format_type: str = "format_1"


# ============================
# 1️⃣ ENDPOINT LEGACY (UPLOAD TXT)
# ============================
@app.post("/parse")
async def parse_txt(
    file: UploadFile = File(...),
    format_type: str = Form("format_1")
):
    uid = str(uuid.uuid4())
    txt_path = f"{UPLOAD_DIR}/{uid}.txt"
    xlsx_path = f"{OUTPUT_DIR}/{uid}.xlsx"

    with open(txt_path, "wb") as f:
        f.write(await file.read())

    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    df = run_parser(text, format_type)
    df.to_excel(xlsx_path, index=False)

    return FileResponse(
        xlsx_path,
        filename="hasil.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================
# 2️⃣ ENDPOINT JSON (DEV / API)
# ============================
@app.post("/parse-text")
def parse_from_text(payload: ParseTextRequest):
    text = payload.text.strip()

    if not text:
        return JSONResponse(
            status_code=400,
            content={"error": "Text tidak boleh kosong"}
        )

    uid = str(uuid.uuid4())
    xlsx_path = f"{OUTPUT_DIR}/{uid}.xlsx"

    df = run_parser(text, payload.format_type)
    df.to_excel(xlsx_path, index=False)

    return FileResponse(
        xlsx_path,
        filename="hasil.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================
# 3️⃣ ENDPOINT USER AWAM ⭐⭐⭐
# ============================
@app.post("/parse-text-raw")
def parse_text_raw(
    text: str = Body(..., media_type="text/plain"),
    format_type: str = "format_1"
):
    text = text.strip()

    if not text:
        return JSONResponse(
            status_code=400,
            content={"error": "Text tidak boleh kosong"}
        )

    uid = str(uuid.uuid4())
    xlsx_path = f"{OUTPUT_DIR}/{uid}.xlsx"

    df = run_parser(text, format_type)
    df.to_excel(xlsx_path, index=False)

    return FileResponse(
        xlsx_path,
        filename="hasil.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
