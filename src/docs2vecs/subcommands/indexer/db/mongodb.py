from typing import Optional

from pymongo import MongoClient
from pymongo import UpdateOne


class MongoDbConnection:
    def __init__(self, connection_string: str, db_name: str, col_name: str) -> None:
        self._client = MongoClient(connection_string)
        self._db = self._client[db_name]
        self._col = self._db[col_name]

    def get_documents(self, filter: Optional[dict] = None):
        return self._col.find(filter)

    def is_document_tracked(self, filter: Optional[dict] = None):
        return self._col.count_documents(filter) > 0

    def update_documents(self, doc_list: list, status_list: list):
        operations = [
            UpdateOne(
                {"chunk.document_id": doc["document_id"]},
                {"$set": {"chunk": doc, "status": {"succeeded": result.succeeded, "error_message": result.error_message}}},
                upsert=True,
            )
            for doc, result in zip(doc_list, status_list)
        ]
        result = self._col.bulk_write(operations)
        print(result)
