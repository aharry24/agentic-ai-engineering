# RAG Pipeline: PDF Chunking and Retrieval (Course-End Project)

An AI document assistant that loads long PDF reports, chunks them, embeds the chunks with OpenAI, stores them in FAISS, and answers questions with semantic search plus GPT.

## Project structure
```
rag_project/
├── data/pdfs/                 # the 3 test documents (Uber & Lyft SEC filings)
├── rag_pipeline.ipynb         # main notebook: all steps, commented
├── rag_pipeline.py            # same code as a plain script
├── requirements.txt
├── .env.example               # copy to .env and add OPENAI_API_KEY
├── outputs/                   # metrics.json + sample_outputs.md (created on run)
├── vectorstore/faiss_index/   # saved FAISS index (created on run)
└── report/
    ├── report_template.md     # report text with metric placeholders
    └── Project_Report.md      # final report, filled in automatically on run
```

## How to run (VS Code)
1. Open the `rag_project` folder in VS Code.
2. In the terminal:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env             # Windows: copy .env.example .env
   ```
3. Put your OpenAI API key in `.env`.
4. Open `rag_pipeline.ipynb`, select the `.venv` kernel, and click **Run All**.
   The first run embeds about 3,000 chunks (roughly 650k tokens, around $0.02 with `text-embedding-3-small`).
5. Save the notebook with its outputs, then zip the folder for submission (leave out `.venv` and `.env`).
