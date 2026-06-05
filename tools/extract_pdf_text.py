from __future__ import annotations

import re
import sys
import zlib
from pathlib import Path


def decode_pdf_string(value: bytes) -> str:
    value = value.replace(rb"\\(", b"\x00").replace(rb"\\)", b"\x01")
    value = re.sub(rb"\\[nrtbf]", b" ", value)
    value = value.replace(b"\x00", b"(").replace(b"\x01", b")")
    return value.decode("latin-1", errors="ignore")


def extract(path: Path) -> str:
    data = path.read_bytes()
    chunks: list[bytes] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw = match.group(1).strip(b"\r\n")
        try:
            chunks.append(zlib.decompress(raw))
        except zlib.error:
            chunks.append(raw)

    text_parts: list[str] = []
    for chunk in chunks:
        for item in re.findall(rb"\((?:\\.|[^\\)])*\)\s*Tj", chunk):
            text_parts.append(decode_pdf_string(item[:-2].strip()[1:-1]))
        for array in re.findall(rb"\[(.*?)\]\s*TJ", chunk, re.S):
            for item in re.findall(rb"\((?:\\.|[^\\)])*\)", array):
                text_parts.append(decode_pdf_string(item[1:-1]))
            text_parts.append(" ")
    return re.sub(r"\s+", " ", " ".join(text_parts)).strip()


if __name__ == "__main__":
    pdf_path = Path(sys.argv[1])
    print(extract(pdf_path))
