from pathlib import Path
from typing import List
from typing import Optional

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class AzureBlobStoreUploaderSkill(IndexerSkill):
    def __init__(self, config: dict, global_config: Config):
        super().__init__(config, global_config)
        self._blob_path = self._config["blob_path"]
        self._container_name = self._config["container_name"]
        self._storage_url = self._config["storage_url"]
        self._blob_name = self._config["blob_name"] if "blob_name" in self._config else None

    def _get_blob_client(self, blob_name):
        credential = DefaultAzureCredential()
        return BlobClient(
            self._storage_url,
            container_name=self._container_name,
            blob_name=blob_name,
            credential=credential,
        )

    def upload_document(self, document: Document, overwrite=False):
        self._blob_name = f"{self._blob_path}/{Path(document.filename).name}"
        self._blob_client = self._get_blob_client(self._blob_name)

        print(f"Uploading {document.filename} to {self._blob_client.url}")

        with Path(document.filename).expanduser().resolve().open(mode="rb") as data:
            try:
                self._blob_client.upload_blob(data=data, overwrite=overwrite)
                print(f"Uploaded {document.filename} to {self._blob_client.url}")
            except ResourceExistsError as err:
                print(f"Blob {self._blob_client.url} already exists: {err}")

    def delete_blob(self, blob_name):
        try:
            self._blob_client = self._get_blob_client(blob_name=blob_name)
            self._blob_client.delete_blob()
            print(f"Deleted {blob_name}")
        except ResourceExistsError as err:
            print(f"Blob doesn't exist: {err}")

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        print("Running AzureBlobStoreUploaderSkill")

        for doc in input:
            self.upload_document(doc)

        return input
