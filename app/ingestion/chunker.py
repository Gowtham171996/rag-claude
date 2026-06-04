from dataclasses import dataclass

import tiktoken

from app.ingestion.parser import ParsedDocument

_enc = tiktoken.get_encoding("cl100k_base")

CHUNK_TOKENS = 512
OVERLAP_TOKENS = 64


@dataclass
class Chunk:
    text: str
    chunk_index: int
    page: int | None
    char_start: int
    char_end: int
    token_count: int


def _chunk_text(text: str, page: int | None, global_offset: int) -> list[Chunk]:
    tokens = _enc.encode(text)
    chunks: list[Chunk] = []
    step = CHUNK_TOKENS - OVERLAP_TOKENS
    chunk_index = 0

    for start in range(0, len(tokens), step):
        end = min(start + CHUNK_TOKENS, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = _enc.decode(chunk_tokens)

        # Approximate character positions
        char_start = global_offset + len(_enc.decode(tokens[:start]))
        char_end = char_start + len(chunk_text)

        chunks.append(
            Chunk(
                text=chunk_text,
                chunk_index=chunk_index,
                page=page,
                char_start=char_start,
                char_end=char_end,
                token_count=len(chunk_tokens),
            )
        )
        chunk_index += 1

        if end == len(tokens):
            break

    return chunks


def chunk_document(doc: ParsedDocument) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    global_offset = 0
    global_index = 0

    for page_num, page_text in enumerate(doc.pages, start=1):
        page = page_num if len(doc.pages) > 1 else None
        page_chunks = _chunk_text(page_text, page=page, global_offset=global_offset)

        for chunk in page_chunks:
            chunk.chunk_index = global_index
            global_index += 1
            all_chunks.append(chunk)

        global_offset += len(page_text)

    return all_chunks
