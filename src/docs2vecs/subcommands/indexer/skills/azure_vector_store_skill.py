from typing import List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import IndexingResult

from docs2vecs.subcommands.indexer.config import Config
from docs2vecs.subcommands.indexer.document import Document
from docs2vecs.subcommands.indexer.document.chunk import Chunk
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill
from docs2vecs.subcommands.indexer.skills.tracker import VectorStoreTracker


class AzureVectorStoreSkill(IndexerSkill):
    def __init__(
        self,
        config: dict,
        global_config: Config,
        vector_store_tracker: VectorStoreTracker = None,
    ):
        super().__init__(config, global_config)
        self._vector_store_tracker = vector_store_tracker
        self._overwrite_index = self._config.get("overwrite_index", False)

        az_credential = (
            AzureKeyCredential(self._config.get("api_key", ""))
            if self._config.get("api_key", "")
            else DefaultAzureCredential()
        )
        self._search_client = SearchClient(
            endpoint=self._config.get("endpoint"),
            index_name=self._config.get("index_name"),
            credential=az_credential,
        )
        self._index_client = SearchIndexClient(
            endpoint=self._config.get("endpoint"), credential=az_credential
        )

        max_batch_size = 50
        self._config["batch_size"] = min(
            max(1, self._config.get("batch_size", max_batch_size)), max_batch_size
        )

    def _upload_embeddings(self, chunks: List[Chunk]):
        field_mapping = self._config.get("field_mapping", {})

        if not field_mapping:
            self.logger.error("No field mapping provided in config file for your index")
            return

        results = []
        if chunks:
            az_ai_search_documents = [
                {
                    field_mapping[key]: getattr(chunk, key)
                    for key in field_mapping
                    if hasattr(chunk, key)
                }
                for chunk in chunks
            ]

            start_idx = 0
            batch_size = self._config.get("batch_size")

            while start_idx < len(az_ai_search_documents):
                batch = az_ai_search_documents[start_idx : start_idx + batch_size]
                results.extend(self._search_client.upload_documents(documents=batch))
                start_idx += batch_size

        return results

    def _update_tracker(self, chunks: List[Chunk], results: List[IndexingResult]):
        if self._vector_store_tracker:
            self._vector_store_tracker.update_documents(chunks, results)

    def _log_upload_results(
        self, chunk_id_list: List[str], results: List[IndexingResult]
    ):
        if self.logger:
            res = [
                {
                    "chunk_id": chunk_id,
                    "succeeded": result.succeeded,
                    "status_code": result.status_code,
                }
                for chunk_id, result in zip(chunk_id_list, results)
            ]
            self.logger.debug(f"Azure AI Search upload results: {res}")

    def _cleanup_index(self):
        self.logger.debug("Cleaning up index...")
        # Get the index definition to find the key field
        index = self._index_client.get_index(self._config.get("index_name"))
        key_field = next(field.name for field in index.fields if field.key)

        # First search for all documents
        results = self._search_client.search(
            search_text="*",
            select=[key_field],
            include_total_count=True,  # Only get the key field as that's all we need for deletion
        )

        # Get all document IDs using the correct key field
        docs_to_delete = [{key_field: doc[key_field]} for doc in results]

        if docs_to_delete:
            # Delete the documents in batches
            self._search_client.delete_documents(documents=docs_to_delete)
            self.logger.debug(f"Deleted {len(docs_to_delete)} documents from the index")

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info("Running AzureVectorStoreSkill")
        if not input:
            return None

        chunks = {}

        if self._vector_store_tracker:
            chunks = {
                chunk.document_id: chunk
                for chunk in self._vector_store_tracker.retrieve_failed_documents()
            }

        self.logger.debug(f"Going to process {len(input)} documents")
        for doc in input:
            self.logger.debug(f"Processing document: {doc.filename}")
            for chunk in doc.chunks:
                if chunk.document_id not in chunks:
                    chunks[chunk.document_id] = chunk

        if not chunks:
            self.logger.debug("No new chunks to upload")
            return input

        if self._overwrite_index:
            self.logger.debug("Cleaning up index before uploading")
            self._cleanup_index()

        upload_results = self._upload_embeddings(chunks.values())
        self._update_tracker(chunks.values(), upload_results)
        self._log_upload_results(list(chunks.keys()), upload_results)

        return input
