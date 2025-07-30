from docs2vecs.subcommands.indexer.skills import FaissVectorStoreSkill
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.document import Chunk
from langchain_community.vectorstores import FAISS
from pathlib import Path
import shutil
from docs2vecs.subcommands.indexer.document.document import Document
from typing import Optional
from typing import List


def test_faiss_vector_store_skill() -> None:
    db_path = Path("tests\\test_index\\my_index_test.faiss")
    files_path = "tests\\test_index\\test_file.txt"

    ids = []
    contents = []
    metadatas = []

    vec_store = FaissVectorStoreSkill(
        config={
            "type": "vector-store",
            "name": "faissdb",
            "params": {
                "collection_name": "test_collection",
                "db_path": db_path,
                "dimension": 384,  # Example dimension, adjust as needed
                "overwrite_index": False,
            },
        },
        global_config=None,
        vector_store_tracker=None,
    )

    chunk_dict_1 = {
        "document_id": "doc_1",
        "document_name": "test_doc",
        "tag": "test_tag",
        "content": "This is a test chunk.",
        "chunk_id": "chunk_1",
        "source_link": files_path,
        "embedding": [0.1] * 384,  # Example embedding
    }

    chunk_dict_2 = {
        "document_id": "doc_2",
        "document_name": "test_doc_2",
        "tag": "test_tag_2",
        "content": "This is a test chunk 2.",
        "chunk_id": "chunk_2",
        "source_link": "random/value/for/chunk_2",
        "embedding": [0.2] * 384,  # Example embedding
    }

    chunk_1 = Chunk()
    chunk_1.document_id = chunk_dict_1["document_id"]
    chunk_1.document_name = chunk_dict_1["document_name"]
    chunk_1.tag = chunk_dict_1["tag"]
    chunk_1.content = chunk_dict_1["content"]
    chunk_1.chunk_id = chunk_dict_1["chunk_id"]
    chunk_1.source_link = chunk_dict_1["source_link"]
    chunk_1.embedding = chunk_dict_1["embedding"]

    chunk_2 = Chunk()
    chunk_2.document_id = chunk_dict_2["document_id"]
    chunk_2.document_name = chunk_dict_2["document_name"]
    chunk_2.tag = chunk_dict_2["tag"]
    chunk_2.content = chunk_dict_2["content"]
    chunk_2.chunk_id = chunk_dict_2["chunk_id"]
    chunk_2.source_link = chunk_dict_2["source_link"]
    chunk_2.embedding = chunk_dict_2["embedding"]

    doc_1 = Document(
        filename="test_doc_1",
        source_url=files_path,
        tag="test_tag_doc_1",
        text="This is the test document 1.",
    )
    doc_1.add_chunk(chunk_1)

    doc_2 = Document(
        filename="test_doc_2",
        source_url=files_path,
        tag="test_tag_doc_2",
        text="This is a test document 2.",
    )
    doc_2.add_chunk(chunk_2)

    input_docs = [doc_1, doc_2]

    # Run the skill with the document
    vec_store.run(input=input_docs)
    # load the database to verify the document was added
    loaded_faiss = FAISS.load_local(
        db_path,
        embeddings=_get_embeddings(input=input_docs),
        allow_dangerous_deserialization=True,
    )
    docstore = loaded_faiss.docstore
    docstore_dict = docstore._dict
    for doc_id, doc in docstore_dict.items():
        ids.append(doc_id)
        contents.append(doc.page_content)
        metadatas.append(doc.metadata)

    list_inserted_metadatas = [
        {"source": chunk_1.source_link, "tags": doc_1.tag},
        {"source": chunk_2.source_link, "tags": doc_2.tag},
    ]

    assert set(ids) == {chunk_1.chunk_id, chunk_2.chunk_id}
    assert set(contents) == {chunk_1.content, chunk_2.content}
    assert _compare_lists_of_dicts(metadatas, list_inserted_metadatas)

    shutil.rmtree(db_path)  # Clean up the test database file


def _get_embeddings(input: Optional[List[Document]] = None) -> List[float]:
    data = []
    for doc in input:
        for chunk in doc.chunks:
            data.append(chunk.embedding)
    return data


def _compare_lists_of_dicts(list1, list2):
    set1 = {tuple(d.items()) for d in list1}
    set2 = {tuple(d.items()) for d in list2}
    return set1 == set2
