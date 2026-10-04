# Auto-exported from rag_pipeline.ipynb - same code, runnable as a script.

# --- Imports and configuration ---------------------------------------------
import os, glob, json, time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader          # PDF -> LangChain Documents (one per page)
from langchain_text_splitters import RecursiveCharacterTextSplitter  # page text -> overlapping chunks
from langchain_openai import OpenAIEmbeddings, ChatOpenAI             # OpenAI embedding + chat models
from langchain_community.vectorstores import FAISS                   # FAISS vector store wrapper
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()  # reads OPENAI_API_KEY (and optional model names) from .env

PDF_DIR        = Path("data/pdfs")
INDEX_DIR      = Path("vectorstore/faiss_index")
OUTPUT_DIR     = Path("outputs")
REPORT_DIR     = Path("report")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL      = os.getenv("CHAT_MODEL", "gpt-4o-mini")
CHUNK_SIZE, CHUNK_OVERLAP = 1000, 200   # characters

OUTPUT_DIR.mkdir(exist_ok=True)
assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY not found - create a .env file from .env.example"
print("Embedding model:", EMBEDDING_MODEL, "| Chat model:", CHAT_MODEL)

pdf_paths = sorted(glob.glob(str(PDF_DIR / "*.pdf")))
for p in pdf_paths:
    print(f"{Path(p).name:<28} {os.path.getsize(p)/1e6:6.2f} MB")
print(f"\n{len(pdf_paths)} PDF files found")

all_pages = []
for path in pdf_paths:
    pages = PyPDFLoader(path).load()          # one Document per page
    all_pages.extend(pages)
    chars = sum(len(p.page_content) for p in pages)
    print(f"{Path(path).name:<28} pages={len(pages):>4}  characters={chars:>10,}")

print(f"\nTotal pages loaded: {len(all_pages)}")
print("\nExample page metadata:", all_pages[0].metadata)
print("Example page text (first 300 chars):\n", all_pages[0].page_content[:300])

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
    add_start_index=True,          # records where in the page each chunk starts
)
chunks = splitter.split_documents(all_pages)

# Drop near-empty chunks (e.g. blank pages / page numbers only)
chunks = [c for c in chunks if len(c.page_content.strip()) > 50]

# --- Chunking metrics --------------------------------------------------------
sizes = [len(c.page_content) for c in chunks]
total_chunks = len(chunks)
avg_chunk_size = sum(sizes) / total_chunks
print(f"Total number of chunks : {total_chunks}")
print(f"Average chunk size     : {avg_chunk_size:.1f} characters")
print(f"Min / max chunk size   : {min(sizes)} / {max(sizes)} characters")

# Per-document breakdown
df = pd.DataFrame({"source": [Path(c.metadata["source"]).name for c in chunks], "chars": sizes})
per_doc = df.groupby("source")["chars"].agg(chunks="count", avg_chars="mean").round(1)
print(per_doc)

for src in per_doc.index:
    doc_chunks = [c for c in chunks if Path(c.metadata["source"]).name == src][:3]
    print("=" * 100)
    print(src)
    for i, c in enumerate(doc_chunks, 1):
        print(f"--- chunk {i} | page {c.metadata['page'] + 1} | {len(c.page_content)} chars")
        print(c.page_content[:400].replace("\n", " "), "...")

embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, chunk_size=500)  # 500 texts per API request
test_vec = embeddings.embed_query("What was the company's total revenue?")
print("Embedding dimension:", len(test_vec))
print("First 8 values:", [round(v, 4) for v in test_vec[:8]])

start = time.time()
if INDEX_DIR.exists():
    vectorstore = FAISS.load_local(str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True)
    print("Loaded existing FAISS index from disk")
else:
    batch = 500
    vectorstore = FAISS.from_documents(chunks[:batch], embeddings)
    for i in range(batch, total_chunks, batch):
        vectorstore.add_documents(chunks[i:i + batch])
        print(f"  embedded {min(i + batch, total_chunks)}/{total_chunks} chunks")
    vectorstore.save_local(str(INDEX_DIR))
    print("Built and saved new FAISS index")

print(f"Vectors in index: {vectorstore.index.ntotal}  |  dimension: {vectorstore.index.d}")
print(f"Time: {time.time() - start:.1f}s")

def retrieve(query, k=3, show=True):
    results = vectorstore.similarity_search_with_score(query, k=k)
    rows = []
    for rank, (doc, dist) in enumerate(results, 1):
        rows.append({
            "rank": rank,
            "source": Path(doc.metadata["source"]).name,
            "page": doc.metadata["page"] + 1,
            "l2_distance": round(float(dist), 4),
            "cosine_sim": round(1 - float(dist) / 2, 4),
            "text": doc.page_content,
        })
    if show:
        print(f"QUERY: {query}\n")
        for r in rows:
            print(f"#{r['rank']}  {r['source']}  p.{r['page']}  cos={r['cosine_sim']}")
    return rows

sample_query = "What were Uber's total revenues for 2021 and how did they change from 2020?"
sample_results = retrieve(sample_query)

top = sample_results[0]
print("\n" + "=" * 100)
print(f"TOP MATCHING CHUNK  ({top['source']}, page {top['page']}, cosine similarity {top['cosine_sim']})")
print("=" * 100)
print(top["text"])

test_queries = [
    "What risks does Lyft describe about drivers being classified as employees instead of independent contractors?",
    "How many Monthly Active Platform Consumers did Uber have in the third quarter of 2022?",
    "How did Lyft's revenue and net loss change in 2021?",
    "What does Uber say about the impact of COVID-19 on its Mobility business?",
]
all_query_results = {sample_query: sample_results}
for q in test_queries:
    all_query_results[q] = retrieve(q)
    print("   top chunk preview:", all_query_results[q][0]["text"][:250].replace("\n", " "), "...\n")

llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

prompt = ChatPromptTemplate.from_template(
    """You are a document assistant for financial filings. Answer the question using ONLY the context below.
If the answer is not in the context, say you don't know. Cite sources as (file, page).

Context:
{context}

Question: {question}
Answer:"""
)

def format_docs(docs):
    return "\n\n".join(f"[{Path(d.metadata['source']).name}, page {d.metadata['page'] + 1}]\n{d.page_content}" for d in docs)

rag_chain = prompt | llm | StrOutputParser()

def ask(question):
    docs = retriever.invoke(question)
    answer = rag_chain.invoke({"context": format_docs(docs), "question": question})
    print(f"Q: {question}\nA: {answer}\n")
    return answer

rag_answers = {q: ask(q) for q in [sample_query] + test_queries}

metrics = {
    "documents": len(pdf_paths),
    "pages": len(all_pages),
    "chunk_size": CHUNK_SIZE,
    "chunk_overlap": CHUNK_OVERLAP,
    "total_chunks": total_chunks,
    "avg_chunk_size": round(avg_chunk_size, 1),
    "min_chunk_size": min(sizes),
    "max_chunk_size": max(sizes),
    "per_document": per_doc.reset_index().to_dict(orient="records"),
    "embedding_model": EMBEDDING_MODEL,
    "embedding_dim": vectorstore.index.d,
    "chat_model": CHAT_MODEL,
}
(OUTPUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))

lines = ["# Sample Query Outputs\n"]
for q, rows in all_query_results.items():
    lines.append(f"## {q}\n")
    lines.append("| Rank | Source | Page | Cosine sim. |\n|---|---|---|---|")
    lines += [f"| {r['rank']} | {r['source']} | {r['page']} | {r['cosine_sim']} |" for r in rows]
    lines.append(f"\n**Top chunk:**\n\n```\n{rows[0]['text']}\n```\n")
    lines.append(f"**GPT answer:** {rag_answers[q]}\n")
(OUTPUT_DIR / "sample_outputs.md").write_text("\n".join(lines), encoding="utf-8")

per_doc_table = "\n".join(f"| {r['source']} | {r['chunks']} | {r['avg_chars']} |" for r in metrics["per_document"])
fill = {
    "{{PAGES}}": str(metrics["pages"]),
    "{{TOTAL_CHUNKS}}": str(total_chunks),
    "{{AVG_CHUNK_SIZE}}": f"{avg_chunk_size:.1f}",
    "{{MIN_CHUNK}}": str(min(sizes)),
    "{{MAX_CHUNK}}": str(max(sizes)),
    "{{PER_DOC_TABLE}}": per_doc_table,
    "{{EMBED_DIM}}": str(vectorstore.index.d),
    "{{SAMPLE_QUERY}}": sample_query,
    "{{TOP_SOURCE}}": f"{top['source']}, page {top['page']}",
    "{{TOP_SCORE}}": str(top["cosine_sim"]),
    "{{TOP_CHUNK}}": top["text"][:1200],
    "{{GPT_ANSWER}}": rag_answers[sample_query].replace("\n", "\n> "),
    "{{EMBEDDING_MODEL}}": EMBEDDING_MODEL,
    "{{CHAT_MODEL}}": CHAT_MODEL,
}
report = (REPORT_DIR / "report_template.md").read_text(encoding="utf-8")
for k, v in fill.items():
    report = report.replace(k, v)
(REPORT_DIR / "Project_Report.md").write_text(report, encoding="utf-8")
print("Saved outputs/metrics.json, outputs/sample_outputs.md, report/Project_Report.md")
print(json.dumps({k: v for k, v in metrics.items() if k != "per_document"}, indent=2))

