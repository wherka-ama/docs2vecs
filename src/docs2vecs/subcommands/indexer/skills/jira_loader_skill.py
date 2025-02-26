import json
from typing import List
from typing import Optional

from jira import JIRA

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class JiraLoaderSkill(IndexerSkill):
    def __init__(self, config: dict, global_config: Config) -> None:
        super().__init__(config, global_config)
        self._set_config_defaults()

        # Initialize Jira client
        self._jira = JIRA(server=self._config["server_url"], token_auth=self._config["api_token"])

    def _set_config_defaults(self):
        """Set default configuration values if not provided"""

        # Required fields that must be provided in config
        required_fields = ["server_url", "api_token", "issues"]
        missing_fields = [field for field in required_fields if field not in self._config]
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        """Run the Jira exporter skill to fetch and process Jira tickets"""
        self.logger.info("Running JiraExporterSkill...")

        # Search for issues using JQL
        # issues = self._jira.search_issues(self._config["jql_query"], maxResults=self._config["max_results"])

        # Search for issues by ID
        jira_issues = [self._jira.issue(issue_id) for issue_id in self._config["issues"]]

        documents = []
        for issue in jira_issues:
            # Create a document for each issue
            doc_content = {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "status": str(issue.fields.status),
                "created": str(issue.fields.created),
                "updated": str(issue.fields.updated),
                "priority": str(issue.fields.priority) if hasattr(issue.fields, "priority") else "None",
                "comments": [
                    {"author": comment.author.displayName, "body": comment.body, "created": str(comment.created)}
                    for comment in issue.fields.comment.comments
                ],
            }

            # Create a Document object
            doc = Document(
                filename=doc_content["key"],
                source_url=doc_content["key"],
                text=json.dumps(doc_content),
            )
            documents.append(doc)

        self.logger.debug(f"Loaded {len(documents)} Jira tickets")

        return documents
