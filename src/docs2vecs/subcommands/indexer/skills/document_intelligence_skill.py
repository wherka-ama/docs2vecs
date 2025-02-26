from pathlib import Path
from typing import List
from typing import Optional

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.identity import DefaultAzureCredential

from docs2vecs.subcommands.indexer.config import Config
from docs2vecs.subcommands.indexer.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class AzureDocumentIntelligenceSkill(IndexerSkill):
    def __init__(self, config: dict, global_config: Config):
        super().__init__(config, global_config)
        self._doc_analysis_client = DocumentAnalysisClient(
            endpoint=self._config["endpoint"],
            credential=DefaultAzureCredential(),
        )

    def _az_di_doc_parser(self, doc_list: List[Document]):
        self.logger.debug(f"Going to process {len(doc_list)} documents")
        for doc in doc_list:
            self.logger.debug(f"Parsing document: {doc.filename}")
            with Path(doc.filename).expanduser().resolve().open(mode="rb") as f:
                poller = self._doc_analysis_client.begin_analyze_document("prebuilt-read", f)
                poller_result = poller.result()
                doc.text = poller_result.to_dict()["content"]

        return doc_list

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info("Running AzureDocumentIntelligenceSkill")

        return self._az_di_doc_parser(input)
