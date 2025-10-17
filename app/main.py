from fastapi import FastAPI

from app.routes import docs_split, doc_status, files_proxy, docs_extract

app = FastAPI(
    title="VDR Extract API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# register routes
@app.get("/health-check")
def health(): return {"status": "up"}


app.include_router(docs_split.router)
app.include_router(doc_status.router)
app.include_router(files_proxy.router)
app.include_router(docs_extract.router)
