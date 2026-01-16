from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI(
        title="DIXITBOT API",
        version="0.1.0",
        description="Backend for DIXITBOT (scraping, KB, MCP, QA via Ollama).",
    )

    # CORS (DEV) — en prod, remplace "*" par ton domaine front
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import des routers ici (évite certains soucis d'import circulaire)
    try:
        from app.api.routes.health import router as health_router
        app.include_router(health_router, tags=["health"])
    except ImportError:
        pass  # Route manquante, à créer

    try:
        from app.api.routes.scrape import router as scrape_router
        app.include_router(scrape_router, prefix="/scrape", tags=["scrape"])
    except ImportError:
        pass

    try:
        from app.api.routes.ask import router as ask_router
        app.include_router(ask_router, tags=["ask"])
    except ImportError:
        pass

    try:
        from app.api.routes.kb import router as kb_router
        app.include_router(kb_router, prefix="/kb", tags=["kb"])
    except ImportError:
        pass

    # plus tard si tu ajoutes :
    # from app.api.routes.mcp import router as mcp_router
    # from app.api.routes.analytics import router as analytics_router

    # plus tard :
    # app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
    # app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

    return app

app = create_app()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=51234,
        reload=True,
    )