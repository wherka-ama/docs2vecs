# Overview
This tool, `docs2vecs` is a library/cli that allows you to vectorize your data, enabling you to create RAG powered applications.

![data_ingestion](./docs/readme/vectorize.gif)


For these applications, `docs2vecs` simplifies the entire process:
* Data ingestion: Use the `indexer` to run the data ingestion pipeline: data retrieval, chunking, embedding, and storing resulting vectors in a Vector DB.
* Build proof of concepts: `docs2vecs` allows you to quickly create a RAG prototype by using a local ChromaDB as vector store and a `server` mode to chat with your data.

# Usage
You can use `docs2vecs` in two ways:
1. Install locally from source - recommended method for now
2. Run from Docker/Podman image. Because the Docker/Podman image is hosted in github under XDLC, you might face some issues when pulling the image.

## Run locally from source
```sh
gh repo clone AmadeusITGroup/docs2vecs
cd docs2vecs
uv run --directory src docs2vecs --help
```

## Run from Docker image

```sh
TODO: add instructions to run docs2vecs using a docker/podman image
```

# Documentation

<details><summary>Expand me if you would like to find out how to vectorize your data</summary>

## Indexer sub-command

The `indexer` sub-command runs an indexer pipeline configured in a config file. This is usually used when you have a lot of data to vectorize and want to run it in a batch.

```bash
docs2vecs indexer --help

usage: docs2vecs indexer [-h] --config CONFIG [--env ENV]
options:
--config CONFIG  Path to the YAML configuration file.
--env ENV        Environment file to load.
```

The `indexer` takes in input two arguments: a **mandatory** config file, and an **optional** environment file.

In the config file you'll need to define a list of skills, a skillset, and an indexer. Note that you may define plenty of skills, but only those enumerated in the skillset will be executed in sequence.

Example:

```bash
docs2vecs indexer --config ~/Downloads/sw_export_temp/config/confluence_process.yml --env ~/indexer.env
```

Please check the [detailed skills documentation](docs/readme/indexer-skills.md).

The config yaml file is validated against [this schema](./src/docs2vecs/subcommands/indexer/config/config_schema.yaml).

Please check this [sample config file](resources/example_data/indexer-config-example.yml).

</details>


<details><summary>Expand me if you would like to find out how create an integrated vectorization in Azure</summary>

## Integrated Vectorization sub-command
`integrated_vec` - Run an integrated vectorization pipeline configured in a config file.

```bash
docs2vecs integrated_vec --help

usage: docs2vecs integrated_vec [-h] --config CONFIG [--env ENV]
options:
--config CONFIG  Path to the YAML configuration file.
--env ENV        Environment file to load.
```

Example:

```bash
docs2vecs integrated_vec --config ~/Downloads/sw_export_temp/config/config.yaml --env ~/integrated_vec .env
```

The config yaml file is validated against [this schema](./src/docs2vecs/subcommands/integrated_vec/config/config_schema.yaml).

Config `yml` file sample:

```yaml
---
integrated_vec:
    id: AzureAISearchIndexer
    skill:
        type: integrated_vec
        name: AzureAISearchIntegratedVectorization
        params:
            search_ai_api_key: env.AZURE_AI_SEARCH_API_KEY
            search_ai_endpoint: http://replace.me.with.your.endpoint
            embedding_endpoint: http://replace.me.with.your.endpoint
            index_name: your_index_name
            indexer_name: new_indexer_name
            skillset_name: new_skillset_name
            data_source_connection_string: ResourceId=/subscriptions/your_subscription_id/resourceGroups/resource_group_name/providers/Microsoft.Storage/storageAccounts/storage_account_name;
            data_source_connection_name: new_connection_name
            encryption_key: env.AZURE_AI_SEARCH_ENCRYPTION_KEY
            container_name: your_container_name

```

</details>

## Important note:
Please note that **api keys** should **NOT** be stored in config files, and should **NOT** be added to `git`. Therefore, if you build your config file, use the `env.` prefix for `api_key` parameter. For example: `api_key: env.AZURE_AI_SEARCH_API_KEY`.

Make sure you export the environment variables before you run the indexer. For convenience you can use the `--env` argument to supply your own `.env` file.

## Experimental features
<details><summary>Tracker</summary>

### Tracker

The tracker feature allows you to monitor and manage the status of documents processed by the indexer. This is particularly useful for tracking failed documents and retrying their processing.

To achieve this, the tracker needs a `MongoDB` connection, which can be defined in the input config file.

The way it works is that each document in `MongoDB` has a `chunk` part having a `document_id`. This `document_id` is actually the hash of the content for that chunk. So, as long as the content is the same, the hash will stay the same. Besides this, there is a `status` property that keeps track whether the upload to vector store was successful or not.

If you'd like to use a different database to keep track of this, you'll have to write your own "driver" similar to the existing [mongodb](./src/docs2vecs/subcommands/indexer/db/mongodb.py). Then you need to add it to the [DBFactory](./src/docs2vecs/subcommands/indexer/skills/factory.py).
</details>

# Development

To run all the tests run:

    tox

Note, to combine the coverage data from all the tox environments run:

| OS      | Command                            |
| :---    | :---                                |
| Windows | `set PYTEST_ADDOPTS=--cov-append tox`   |
| Other   | `PYTEST_ADDOPTS=--cov-append tox`       |
