from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import check_database, init_db
from app.routers.auth import router as auth_router
from app.routers.cadastros import router as cadastros_router
from app.routers.ordens import router as ordens_router
from app.routers.produtos import router as produtos_router
from app.routers.usuarios import router as usuarios_router

settings = get_settings()
if settings.is_production and (problemas := settings.problemas_producao()):
    raise RuntimeError("Configuração insegura para produção:\n- " + "\n- ".join(problemas))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(cadastros_router)
app.include_router(produtos_router)
app.include_router(ordens_router)

@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    parts: list[str] = []
    for err in exc.errors():
        msg = str(err.get("msg", "valor inválido")).removeprefix("Value error, ")
        loc = [str(item) for item in err.get("loc", []) if item not in ("body", "query") and not isinstance(item, int)]
        parts.append(f"{loc[-1]}: {msg}" if loc and err.get("type") != "value_error" else msg)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "; ".join(parts) or "Dados inválidos."},
    )


@app.get("/health")
def health() -> dict:
    return {"ok": True, "database": check_database()}


@app.get("/")
def root() -> dict:
    return {"name": settings.app_name, "version": settings.app_version}
