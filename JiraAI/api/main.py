from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from JiraAI.api.routes import business, dev

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(business.router, prefix="/business")
app.include_router(dev.router, prefix="/dev")
