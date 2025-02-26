import json
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import IndexingSchedule
from azure.search.documents.indexes.models import SearchIndexer
from azure.search.documents.indexes.models import SearchIndexerDataSourceConnection
from azure.search.documents.indexes.models import SearchIndexerDataSourceType
from azure.search.documents.indexes.models import SearchIndexerSkillset

from docs2vecs.subcommands.indexer import config as cfg_module
from docs2vecs.subcommands.indexer.config import Config
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class IntegratedVec(IndexerSkill):
    def __init__(self, config: dict, global_config: Config):
        super().__init__(config, global_config)
        self._search_ai_endpoint = self._config["search_ai_endpoint"]
        self._search_ai_api_key = self._config["search_ai_api_key"]
        self._index_name = self._config["index_name"]
        self._indexer_name = self._config["indexer_name"]
        self._skillset_name = self._config["skillset_name"]
        self._embedding_endpoint = self._config["embedding_endpoint"]
        self._embedding_deployment_name = self._config["embedding_deployment_name"]
        self._data_source_connection_string = self._config["data_source_connection_string"]
        self._data_source_connection_name = self._config["data_source_connection_name"]
        self._encryption_key = self._config["encryption_key"]
        self._container_name = self._config["container_name"]
        if self._encryption_key:
            self._encryption_key = json.loads(self._encryption_key)
        self._search_ai_client = SearchIndexerClient(
            endpoint=self._search_ai_endpoint,
            index_name=self._index_name,
            credential=DefaultAzureCredential(),
        )

    def get_skill(skill_config_dict: dict, global_config: Config):
        if skill_config_dict["name"] == "AzureAISearchIntegratedVectorization":
            return IntegratedVec(skill_config_dict, global_config)
        raise ValueError(f"Unknown skillset creation skill: {skill_config_dict['name']}")

    def create_data_source_connection(self):
        data_source_connection = SearchIndexerDataSourceConnection(
            name=self._data_source_connection_name,
            type=SearchIndexerDataSourceType.AZURE_BLOB,
            connection_string=self._data_source_connection_string,
            container={"name": self._container_name},
            encryption_key=self._encryption_key,
        )
        try:
            print(f"Creating Data Source Connection '{self._data_source_connection_name}' ...")
            self._search_ai_client.create_data_source_connection(data_source_connection)
            print(f"Data Source Connection '{self._data_source_connection_name}' created successfully.")
        except Exception as ex:
            print(ex)

    def _create_skillset(self):
        skills = [
            {
                "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                "name": "cne-genai-split-skill",
                "description": "Split skill to chunk documents",
                "context": "/document",
                "defaultLanguageCode": "en",
                "textSplitMode": "pages",
                "maximumPageLength": 300,
                "pageOverlapLength": 0,
                "maximumPagesToTake": 0,
                "unit": "characters",
                "inputs": [{"name": "text", "source": "/document/content"}],
                "outputs": [{"name": "textItems", "targetName": "chunked_text"}],
                "azureOpenAITokenizerParameters": None,
            },
            {
                "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                "name": "cne-genai-embedding-skill",
                "description": "Connects a deployed embedding model.",
                "context": "/document/chunked_text/*",
                "resourceUri": self._embedding_endpoint,
                "apiKey": None,
                "deploymentId": self._embedding_deployment_name,
                "dimensions": 1536,
                "modelName": self._embedding_deployment_name,
                "inputs": [{"name": "text", "source": "/document/chunked_text/*"}],
                "outputs": [{"name": "embedding", "targetName": "openai_embedding"}],
                "authIdentity": None,
            },
        ]

        index_projections = {
            "selectors": [
                {
                    "targetIndexName": self._index_name,
                    "parentKeyFieldName": "document_id",
                    "sourceContext": "/document/chunked_text/*",
                    "mappings": [
                        {"name": "content", "source": "/document/chunked_text/*", "sourceContext": None, "inputs": []},
                        {"name": "embedding", "source": "/document/chunked_text/*/openai_embedding", "sourceContext": None, "inputs": []},
                        {"name": "document_name", "source": "/document/metadata_storage_name", "sourceContext": None, "inputs": []},
                    ],
                }
            ],
            "parameters": {"projectionMode": "skipIndexingParentDocuments"},
        }

        skillset = SearchIndexerSkillset(
            name=self._skillset_name,
            description="Skillset for document chunking and applying OpenAI embeddings.",
            skills=skills,
            index_projection=index_projections,
            encryption_key=self._encryption_key,
        )

        try:
            print(f"Creating Skillset '{self._skillset_name}'...")
            self._search_ai_client.create_skillset(skillset)
            print(f"Skillset '{self._skillset_name}' created successfully.")
        except Exception as ex:
            print(ex)

    def _create_indexer(self):
        indexer_config = SearchIndexer(
            name=self._indexer_name,
            description="Indexer performing integrated vectorization with data source of Azure Blob Storage",
            data_source_name=self._data_source_connection_name,
            target_index_name=self._index_name,
            skillset_name=self._skillset_name,
            schedule=IndexingSchedule(interval="P1D"),
            parameters={
                "batchSize": None,
                "maxFailedItems": None,
                "maxFailedItemsPerBatch": None,
                "base64EncodeKeys": None,
                "configuration": {"allowSkillsetToReadFileData": True},
            },
            field_mappings=[],
            output_field_mappings=[],
            encryption_key=self._encryption_key,
        )

        try:
            print(f"Creating Indexer '{self._indexer_name}'...")
            self._search_ai_client.create_indexer(indexer_config)
            print(f"Indexer '{self._indexer_name}' created successfully.")
        except Exception as ex:
            print(ex)

    def run(self):
        print("Running Integrated Vectorization Flow")
        self._create_skillset()
        self.create_data_source_connection()
        self._create_indexer()
        return {"status": "Integrated Vectorization Flow Completed"}


def run_integrated_vec(args):
    config_schema = Path(cfg_module.__file__).parent.parent.parent / "integrated_vec" / "config" / "config_schema.yaml"
    config = Config(args.config, config_schema)
    skill_config = config.config["integrated_vec"]["skill"]
    if skill_config.get("name") == "AzureAISearchIntegratedVectorization":
        integratedVectorization = IntegratedVec(skill_config, config)
        integratedVectorization.run()
    else:
        raise ValueError(f"Unknown skill: {skill_config.get('name')}")
