from abc import ABC
from abc import abstractmethod
from typing import List
from typing import Optional

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document import Document

from .logger import get_logger


class IndexerSkill(ABC):
    """
    Base class for all indexer skills.
    """

    def __init__(self, skill_config: dict, global_config: Config) -> None:
        self._config = skill_config.get("params", {})
        self._global_config = global_config
        log_file = "logs/indexer_skills.log"
        self.logger = get_logger(self.__class__.__name__, log_file=log_file)

    @abstractmethod
    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        """Execute the skill's main functionality.

        Args:
            input: Optional list of documents to process. Some skills may not require input.

        Returns:
            List of processed documents
        """


class FileLoaderSkill(IndexerSkill):
    def __init__(self, skill_config: dict, global_config: Config) -> None:
        super().__init__(skill_config, global_config)
