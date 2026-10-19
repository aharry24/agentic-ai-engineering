# RAG Pipeline: PDF Chunking and Retrieval

An AI document assistant that loads long PDF reports, chunks them, embeds the chunks with OpenAI, stores them in FAISS, and answers questions with semantic search plus GPT.

## Project structure
```
rag_project/
├── data/pdfs/                 # the 3 test documents (Uber & Lyft SEC filings)
├── rag_pipeline.ipynb         # main notebook: all steps, commented
├── rag_pipeline.py            # same code as a plain script
├── requirements.txt
├── .env.example               # copy to .env and add OPENAI_API_KEY
├── outputs/                   
    └── metrics.json           # created on run
    └── sample_outputs.md      # created on run
├── vectorstore/faiss_index/   # saved FAISS index (created on run)
└── report/
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

## How to run (Google Colab)
No local setup is needed. The Colab notebook installs its own packages and keeps its files in your Google Drive.

1. Go to [colab.research.google.com](https://colab.research.google.com) and choose **File → Upload notebook**, then pick `rag_pipeline.ipynb`.
2. Add your API key: click the 🔑 **Secrets** icon in the left sidebar, add a secret named `OPENAI_API_KEY`, paste your key, and switch **Notebook access** on. (If you skip this, the notebook asks for the key when it runs.)
3. Add the PDFs, either way works:
   - Upload `uber_2021.pdf`, `lyft_2021.pdf` and `uber_10q_sept_2022.pdf` to `MyDrive/rag_project/data/pdfs/` in Google Drive, or
   - Leave that folder empty. The notebook shows an upload button when it reaches Section 1.
4. To generate `Project_Report.md`, upload it to `MyDrive/rag_project/report/`. Without it, the notebook still saves the metrics and sample outputs and skips the report.
5. Click **Runtime → Run all**. Allow Google Drive access when Colab asks.
   The first run embeds about 3,000 chunks (roughly 650k tokens, around $0.02 with `text-embedding-3-small`). The FAISS index is saved to Drive, so later runs load it instead of re-embedding.
6. Get the results from `MyDrive/rag_project/outputs/` and `report/`, or run the last cell to download them as a zip.
7. Save the notebook with its outputs (**File → Download → Download .ipynb**) for submission.

Notes:
- To work without Google Drive, set `USE_DRIVE = False` in the Drive cell. Files then go to `/content/rag_project`, which is deleted when the runtime disconnects, so the index has to be rebuilt each session.
- Don't copy a `vectorstore/` folder built on your own computer into Drive. Let Colab build its own index so the FAISS and LangChain versions match.
