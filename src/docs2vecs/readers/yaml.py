from pathlib import Path
from typing import Dict, List, Optional

from fsspec import AbstractFileSystem
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document

"""A reader for YAML files that implements the BaseReader interface.
This class reads YAML documents from a file and converts them into a list of Document objects.
Each YAML document in the file is processed separately and converted into a Document with its
text content and metadata.
Attributes:
    None
Methods:
    load_data: Reads YAML documents from a file and returns a list of Document objects.
Raises:
    ImportError: If the yaml module is not installed.
"""


class YamlReader(BaseReader):
    """Load and process YAML documents from a file.
    This function reads YAML documents from a file and converts them into Document objects.
    Each YAML document is processed and stored with metadata including 'kind' and 'scope'.
    Args:
        file (Path): Path to the YAML file to be processed
        extra_info (Optional[Dict], optional): Additional information to be included. Defaults to None.
        fs (Optional[AbstractFileSystem], optional): File system abstraction. Defaults to None.
    Returns:
        List[Document]: List of Document objects, each containing:
            - text: The YAML document content as a string
            - metadata: Dictionary with 'kind' and 'scope' information
    Raises:
        ImportError: If the yaml module is not installed
    Note:
        - The function removes '__start_line__' and '__yaml_file__' fields from documents if present
        - Prints progress message for every 100 documents processed
        - Documents with processing errors are skipped with error messages printed
    """

    def load_data(
        # self,
        file: Path,
        extra_info: Optional[Dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> List[Document]:
        # def load_data(self, file: Path, extra_info: Optional[Dict] = None) -> List[Document]:
        data = []
        try:
            import yaml
        except ImportError as err:
            raise ImportError("yaml module is required to read YAML files.") from err

        counter = 0
        with Path.open(file) as fp:
            # the file contains a list of yaml documents; we read them one by one and add them to the list
            for doc in yaml.safe_load_all(fp):
                counter += 1
                if counter % 100 == 0:
                    print(f"Processed {counter} documents")
                # print(doc)
                # if counter > 10000:
                #     break

                doc_copy = doc.copy()
                if "__start_line__" in doc_copy:
                    del doc_copy["__start_line__"]
                    del doc_copy["__yaml_file__"]

                try:
                    data.append(
                        Document(
                            text=str(yaml.safe_dump(doc_copy)),
                            metadata={
                                "kind": doc.get("kind", "-"),
                                "scope": doc.get("metadata", {}).get("scope", "-"),
                            },
                        )
                    )
                except Exception as e:
                    print(f"Error processing document {counter}: {e}")

        return data
