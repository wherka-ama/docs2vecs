from io import StringIO
from pathlib import Path

from dotenv import load_dotenv

from docs2vecs.subcommands.indexer.config.config import Config


def test_config():
    dotenv_stream = StringIO(
        "SWE_AUTH_TOKEN=abc\nAZURE_DOCUMENT_INTELLIGENCE_API_KEY=abc123\nAZURE_EMBEDDING_API_KEY=abc234\nAZURE_AI_SEARCH_API_KEY=abc345"
    )
    load_dotenv(stream=dotenv_stream)
    config_file = Path("tests/test_data/test_config.yaml")
    schema_file = Path("src/docs2vecs/subcommands/indexer/config/config_schema.yaml")
    config = Config(config_file, schema_file)
    assert config is not None

    actual_skill_config_list = list(config.get_skills_config_dict())

    actual_exporter_config = next(
        filter(
            lambda skill_config: skill_config["type"] == "exporter",
            actual_skill_config_list,
        ),
        None,
    )
    expected_exporter_config = {
        "type": "exporter",
        "name": "scrollword-exporter",
        "params": {
            "api_url": "https://scroll-word-exporter/url",
            "auth_token": "abc",
            "poll_interval": 2,
            "export_folder": "~/Downloads/sw_export_temp",
        },
    }
    assert actual_exporter_config is not None
    assert actual_exporter_config == expected_exporter_config

    actual_document_parser_config = next(
        filter(
            lambda skill_config: skill_config["type"] == "file-reader",
            actual_skill_config_list,
        ),
        None,
    )
    expected_document_parser_config = {
        "type": "file-reader",
        "name": "azure-document-intelligence",
        "params": {
            "api_key": "abc123",
            "endpoint": "https://test-az-di.azure.com",
        },
    }
    assert actual_document_parser_config is not None
    assert actual_document_parser_config == expected_document_parser_config

    actual_embedding_config = next(
        filter(
            lambda skill_config: skill_config["type"] == "embedding",
            actual_skill_config_list,
        ),
        None,
    )
    expected_embedding_config = {
        "type": "embedding",
        "name": "azure-ada002-embedding",
        "params": {
            "endpoint": "https://test-embedding.openai.azure.com",
            "api_key": "abc234",
            "api_version": "2024-02-15-preview",
            "deployment_name": "text-embedding-ada-002",
        },
    }
    assert actual_embedding_config is not None
    assert actual_embedding_config == expected_embedding_config

    actual_vector_store_config = next(
        filter(
            lambda skill_config: skill_config["type"] == "vector-store",
            actual_skill_config_list,
        ),
        None,
    )
    expected_vector_store_config = {
        "type": "vector-store",
        "name": "azure-ai-search",
        "params": {
            "api_key": "abc345",
            "endpoint": "https://test-search.search.windows.net",
            "index_name": "knowledge-for-copilot",
        },
    }
    assert actual_vector_store_config is not None
    assert actual_vector_store_config == expected_vector_store_config
