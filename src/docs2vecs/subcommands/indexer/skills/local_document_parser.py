from typing import List
from typing import Optional

from llama_index.core import SimpleDirectoryReader

from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class LocalDocumentParser(IndexerSkill):
    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        print("Running LocalDocumentParser...\n")

        data = []
        for document_dir in self._global_config.get_data_source_config_dict()["document_dirs"]:
            data += SimpleDirectoryReader(
                input_dir=document_dir, recursive=self._config["recursive"], exclude=self._config.get("exclude", None)
            ).load_data()

        doc_list = []
        for d in data:
            indexer_document: Document = Document(
                filename=d.metadata["file_path"],
                source_url=d.metadata["file_path"],
                text=d.text,
            )
            doc_list.append(indexer_document)

        return doc_list
