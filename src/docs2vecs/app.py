import os
import os.path
from pathlib import Path

from chromadb.app import app as chromadb_extended_app
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastembed.text import TextEmbedding

from docs2vecs.core import (
    EmbeddingModelLoader,
    LlamaIndexEmbeddingAdapter,
    get_client,
    get_embeddings,
)

MODEL = os.environ.get("DOCS2VECS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CACHE_DIR = os.environ.get("DOCS2VECS_CACHE_DIR", "./.cache")
CHROMA_DIR = os.environ.get("PERSIST_DIRECTORY", "./chroma")


def fetch_nearest_neighbors(collection_name: str, n_results: int, prompt: str):
    chroma_client = get_client(CHROMA_DIR)

    loader = EmbeddingModelLoader(CACHE_DIR)
    embed_model = loader.get_model(MODEL)
    embedding_function = LlamaIndexEmbeddingAdapter(embed_model)

    collection = chroma_client.get_or_create_collection(
        collection_name, embedding_function=embedding_function
    )

    query_results = collection.query(query_texts=[prompt], n_results=n_results)
    return query_results


@chromadb_extended_app.post("/api/v1/embeddings")
@chromadb_extended_app.get("/api/v1/embeddings")
async def embeddings(data: Request):
    payload = ""
    if data.method == "GET":
        payload = data.query_params.get("data")
    else:
        payload = (await data.json()).get("data")
    return get_embeddings(payload, MODEL, CACHE_DIR)


@chromadb_extended_app.post(
    "/api/v1/collections/{collection_name}/{n_results}/get_nearest_neighbors"
)
async def get_nearest_neighbors_from_prompt(
    collection_name: str, n_results: int, data: Request
):
    prompt = (await data.json()).get("query")
    query_results = fetch_nearest_neighbors(collection_name, n_results, prompt)
    return JSONResponse(query_results.get("documents", []))


@chromadb_extended_app.get(
    "/api/v1/collections/{collection_name}/{n_results}/get_nearest_neighbors"
)
async def get_nearest_neighbors(collection_name: str, n_results: int, query: str):
    prompt = query
    if not prompt:
        return JSONResponse([])

    query_results = fetch_nearest_neighbors(collection_name, n_results, prompt)
    return JSONResponse(query_results.get("documents", []))


@chromadb_extended_app.get("/api/v1/supported_models")
async def get_supported_models():
    return JSONResponse(content=TextEmbedding.list_supported_models())


@chromadb_extended_app.get("/api/v1/collections/{collection_name}/documents")
async def get_documents(collection_name: str, limit: int = 10):
    chroma_client = get_client(CHROMA_DIR)
    documents = []
    limit = None if limit == 0 else limit
    if any(
        collection_name == collection for collection in chroma_client.list_collections()
    ):
        documents = chroma_client.get_collection(collection_name).get(limit=limit)[
            "documents"
        ]

    return JSONResponse(documents)


@chromadb_extended_app.get("/api/v1/list-collections")
async def list_collections():
    print("list_collections endpoint")
    chroma_client = get_client(CHROMA_DIR)
    collections = chroma_client.list_collections()
    return JSONResponse([{"name": col} for col in collections])


chromadb_extended_app.mount(
    "/static",
    StaticFiles(directory=Path(Path(__file__).parent / "static")),
    name="static",
)


@chromadb_extended_app.get("/")
async def root():
    return FileResponse(Path(Path(__file__).parent / "static", "index.html"))
