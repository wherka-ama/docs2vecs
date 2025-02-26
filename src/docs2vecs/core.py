import contextlib
import json
import os
import time
import warnings
from functools import lru_cache

import chromadb
import requests
import Stemmer
import uvicorn
from chromadb import Documents, EmbeddingFunction, Embeddings
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.schema import TextNode
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from urllib3.exceptions import InsecureRequestWarning

# TODO: adding the YamlReader temporarily - it should be inferred based on the configuration i.e. only when AUD is processed
from .readers.yaml import YamlReader

old_merge_environment_settings = requests.Session.merge_environment_settings


@contextlib.contextmanager
def no_ssl_verification():
    # Based on https://stackoverflow.com/a/15445989
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(
            self, url, proxies, stream, verify, cert
        )
        settings["verify"] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings

        for adapter in opened_adapters:
            try:
                adapter.close()
            except Exception as e:
                print(
                    f"Warning: It was not possible to close the adapter {adapter}: {e}"
                )


class LlamaIndexEmbeddingAdapter(EmbeddingFunction):
    def __init__(self, ef: BaseEmbedding):
        self.ef = ef

    def __call__(self, input: Documents) -> Embeddings:
        # print("LlamaIndexEmbeddingAdapter - input", input)
        # print([node.embedding for node in self.ef([TextNode(text=doc) for doc in input])])
        return [
            node.embedding for node in self.ef([TextNode(text=doc) for doc in input])
        ]


class EmbeddingModelLoader:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.models = {}

    def get_model(self, model_name):
        print(f"Loading model: {model_name}")

        if model_name == "text-embedding-ada-002":
            return AzureOpenAIEmbedding(
                deployment_name=os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME"),
                api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
                azure_endpoint=os.getenv("AZURE_EMBEDDING_ENDPOINT"),
                api_version=os.getenv("AZURE_EMBEDDING_API_VERSION"),
            )

        if model_name not in self.models:
            with no_ssl_verification():
                self.models[model_name] = FastEmbedEmbedding(
                    model_name=model_name, cache_dir=self.cache_dir
                )
        return self.models[model_name]


def get_client(db):
    if db and db.startswith("http"):
        return chromadb.HttpClient(db)
    elif db:
        return chromadb.PersistentClient(db)

    return chromadb.EphemeralClient()


def get_collection(db, collection, model):
    chroma_client = get_client(db)
    embed_model = None
    with no_ssl_verification():
        embed_model = FastEmbedEmbedding(model_name=model)

    Settings.embed_model = embed_model
    Settings.llm = None

    col = chroma_client.get_or_create_collection(
        collection, embedding_function=LlamaIndexEmbeddingAdapter(embed_model)
    )
    return col


def get_index(col):
    vector_store = ChromaVectorStore(chroma_collection=col)

    metadatas = col.get()["metadatas"]

    # Build Docstore
    docstore_dict = {}
    for metadata in metadatas:
        node_metadata = json.loads(metadata["node"])
        docstore_dict[node_metadata["id_"]] = {
            "__data__": node_metadata,
            "__type__": "1",
        }

    docstore = SimpleDocumentStore.from_dict({"docstore/data": docstore_dict})

    storage_context = StorageContext.from_defaults(
        docstore=docstore, vector_store=vector_store
    )

    return VectorStoreIndex(nodes=[], storage_context=storage_context)


def feed_db(args):
    documents = []
    for document_dir in args.document_dirs:
        documents += SimpleDirectoryReader(
            input_dir=document_dir,
            recursive=True,
            exclude=[".git"],
            file_extractor={".yaml": YamlReader, ".yml": YamlReader},
        ).load_data()

    chroma_client = get_client(args.db)
    embed_model = None
    with no_ssl_verification():
        loader = EmbeddingModelLoader(args.cache_dir)
        embed_model = loader.get_model(args.model)

    col = chroma_client.get_or_create_collection(
        args.collection, embedding_function=LlamaIndexEmbeddingAdapter(embed_model)
    )

    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=embed_model,
    )

    # get the current time to measure the time of the indexing
    start_time = time.time()

    nodes = splitter.get_nodes_from_documents(documents)
    # get the time after the indexing
    end_indexing_time = time.time()
    print(f"Indexing took {end_indexing_time - start_time} seconds")

    # add nodes to the collection, do it in batches of 1000
    for i in range(0, len(nodes), 1000):
        col.add(
            ids=[n.id_ for n in nodes[i : i + 1000]],
            documents=[node.get_content() for node in nodes[i : i + 1000]],
            metadatas=[{"node": node.to_json()} for node in nodes[i : i + 1000]],
        )

    # get insertion time
    end_insertion_time = time.time()
    print(f"Insertion took {end_insertion_time - end_indexing_time} seconds")


@lru_cache(maxsize=128)
def get_embeddings(data: str, model: str, cache_dir: str):
    loader = EmbeddingModelLoader(cache_dir)
    embed_model = loader.get_model(model)
    embedding_function = LlamaIndexEmbeddingAdapter(embed_model)

    return embedding_function([data])


def start_server(args):
    os.environ["PERSIST_DIRECTORY"] = args.path
    os.environ["DOCS2VECS_MODEL"] = args.model
    os.environ["DOCS2VECS_CACHE_DIR"] = args.cache_dir

    # set ENV variable for PERSIST_DIRECTORY to path
    os.environ["IS_PERSISTENT"] = "True"
    # os.environ["PERSIST_DIRECTORY"] = path
    os.environ["CHROMA_SERVER_NOFILE"] = "65535"
    os.environ["CHROMA_CLI"] = "True"

    if args.model == "text-embedding-ada-002":
        mandatory_env_vars = [
            "AZURE_EMBEDDING_DEPLOYMENT_NAME",
            "AZURE_EMBEDDING_API_KEY",
            "AZURE_EMBEDDING_ENDPOINT",
            "AZURE_EMBEDDING_API_VERSION",
        ]
        for var in mandatory_env_vars:
            if var not in os.environ:
                raise ValueError(
                    f"Missing mandatory environment variable: {var}\nMake sure you have the following env vars properly set: {mandatory_env_vars}"
                )

    uvicorn.run(
        host=args.host or "localhost",
        port=int(args.port or "8000"),
        workers=args.workers or 1,
        log_level=args.log_level or "info",
        # log_config=log_config,
        app="docs2vecs.app:chromadb_extended_app",
        timeout_keep_alive=30,
    )


def get_nearest_neighbors_from_prompt(args):
    db, collection, model, hybrid, prompt = (
        args.db,
        args.collection,
        args.model,
        args.hybrid,
        args.prompt,
    )
    top_k = int(args.top_k)

    col = get_collection(db, collection, model)

    if not hybrid:
        query_results = col.query(query_texts=[prompt], n_results=top_k)
        for i, result in enumerate(query_results["documents"][0]):
            print(f"{i+1}. {result}")
    else:
        index = get_index(col)

        retriever = QueryFusionRetriever(
            [
                index.as_retriever(similarity_top_k=top_k),
                BM25Retriever.from_defaults(
                    docstore=index.docstore,
                    similarity_top_k=top_k,
                    stemmer=Stemmer.Stemmer("english"),
                    language="english",
                ),
            ],
            similarity_top_k=top_k,
            mode="reciprocal_rerank",
            num_queries=1,
            use_async=True,
        )

        nodes = retriever.retrieve(prompt)

        for i, node in enumerate(nodes):
            print(f"{i+1}. {node.get_content()}")
    return
