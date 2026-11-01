from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import (
    tenders, rag, proposals, exports,
    auth, dashboard, tender_details, knowledge, orchestration,
)
from app.routers import (
    tenders, rag, proposals, exports,
    auth, dashboard, tender_details, knowledge, orchestration, assistant,
)

app = FastAPI(title="OliveSoft RFP Intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(tenders.router)
app.include_router(tender_details.router)
app.include_router(tender_details.proposal_router)
app.include_router(rag.router)
app.include_router(knowledge.router)
app.include_router(proposals.router)
app.include_router(exports.router)
app.include_router(orchestration.router)
app.include_router(assistant.router)