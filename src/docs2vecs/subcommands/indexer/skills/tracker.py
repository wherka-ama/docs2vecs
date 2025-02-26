from typing import List
from typing import Optional

from docs2vecs.subcommands.indexer.document.chunk import Chunk


class VectorStoreTracker:
    def __init__(self, db_connection=None) -> None:
        self._db_connection = db_connection

    def get_documents(self, filter: Optional[dict] = None):
        return self._db_connection.get_documents(filter)

    def retrieve_failed_documents(self) -> List[Chunk]:
        return [Chunk.FromDict(failed_doc["chunk"]) for failed_doc in self._db_connection.get_documents({"status.succeeded": False})]

    def update_documents(self, document_list: List[Chunk], result_list: list):
        self._db_connection.update_documents([x.to_dict() for x in document_list], result_list)

    def is_document_tracked(self, document_id: str) -> bool:
        return self._db_connection.is_document_tracked({"chunk.document_id": document_id})
