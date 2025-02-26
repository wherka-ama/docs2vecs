"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mdocs2vecs` python will execute
    ``__main__.py`` as a script. That means there will not be any
    ``docs2vecs.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there"s no ``docs2vecs.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

import argparse
from pathlib import Path

from .core import feed_db, get_nearest_neighbors_from_prompt, start_server
from .subcommands.indexer import indexer
from .subcommands.integrated_vec import integrated_vec

parser = argparse.ArgumentParser(
    description="docs2vecs is a command line tool to convert documents to vectors in nice and easy way. No fuss."
)
subparsers = parser.add_subparsers(help="sub-command help")

feed_db_parser = subparsers.add_parser(
    "feed_db", help="Feed the database with documents."
)
feed_db_parser.add_argument(
    "--env", metavar="ENV", required=False, help="Environment file to load."
)
feed_db_parser.add_argument(
    "--document_dirs",
    metavar="DOCUMENTS",
    nargs=argparse.ONE_OR_MORE,
    type=Path,
    help="A list of paths to documents.",
)
feed_db_parser.add_argument(
    "--collection",
    metavar="COLLECTION",
    help="A name for the collection.",
)
feed_db_parser.add_argument(
    "--db",
    metavar="DATABASE",
    help="A path or a connection string to the database.",
)

feed_db_parser.add_argument(
    "--model",
    metavar="MODEL",
    default="sentence-transformers/all-MiniLM-L6-v2",
    help="A name of the embedding model(as per huggingface coordinates).",
)

feed_db_parser.add_argument(
    "--cache_dir",
    metavar="CACHE_DIR",
    default="./.cache",
    help="A path to the cache directory.",
)

feed_db_parser.add_argument(
    "--chunk_size",
    metavar="CHUNK_SIZE",
    type=int,
    default=1024,
    help="A chunk size for the splitter.",
)
feed_db_parser.set_defaults(func=feed_db)

# chroma_parser = subparsers.add_parser("chroma", help="Start the database.")
# chroma_parser.set_defaults(func=start_db)

server_parser = subparsers.add_parser(
    "server", help="Start the extended chroma server with embeddings"
)
server_parser.set_defaults(func=start_server)

server_parser.add_argument(
    "--host", metavar="HOST", default="localhost", help="A host for the server."
)
server_parser.add_argument(
    "--port", metavar="PORT", default=8008, help="A port for the server."
)
server_parser.add_argument(
    "--model",
    metavar="MODEL",
    default="sentence-transformers/all-MiniLM-L6-v2",
    help="A name of the embedding model(as per huggingface coordinates).",
)
server_parser.add_argument(
    "--cache_dir",
    metavar="CACHE_DIR",
    default="./.cache",
    help="A path to the cache directory.",
)
# we need also an optional path parameter - default would be ./chroma_data
server_parser.add_argument(
    "--path", metavar="PATH", default="/chroma_data", help="A path for the server."
)

# workers=args.workers or 1, log_level=args.log_level
server_parser.add_argument(
    "--workers",
    metavar="WORKERS",
    default=1,
    type=int,
    help="Number of workers for the server.",
)
server_parser.add_argument(
    "--log_level", metavar="LOG_LEVEL", default="info", help="Log level for the server."
)
server_parser.add_argument(
    "--env", metavar="ENV", required=False, help="Environment file to load."
)

get_db_parser = subparsers.add_parser(
    "closest", help="Get the closest documents to the prompt."
)
get_db_parser.add_argument(
    "--db",
    metavar="DATABASE",
    help="A path or a connection string to the database.",
)
get_db_parser.add_argument(
    "--collection",
    metavar="COLLECTION",
    help="A name for the collection.",
)
get_db_parser.add_argument(
    "--model",
    metavar="MODEL",
    default="sentence-transformers/all-MiniLM-L6-v2",
    help="A name of the embedding model(as per huggingface coordinates).",
)
get_db_parser.add_argument(
    "--hybrid",
    metavar="HYBRID",
    default=False,
    help="Enable hybrid search (combine keyword and vector search).",
)
get_db_parser.add_argument(
    "--top_k",
    metavar="TOP_K",
    default=4,
    help="A number of the closest documents to return.",
)
get_db_parser.add_argument(
    "prompt",
    metavar="PROMPT",
    help="Input prompt from which to find the closest documents.",
)

get_db_parser.set_defaults(func=get_nearest_neighbors_from_prompt)

indexer_parser = subparsers.add_parser("indexer", help="Run an indexer pipeline")
indexer_parser.set_defaults(func=indexer.run_indexer)
indexer_parser.add_argument(
    "--config",
    metavar="CONFIG",
    required=True,
    help="Path to the YAML configuration file.",
)
indexer_parser.add_argument(
    "--env", metavar="ENV", required=False, help="Environment file to load."
)

integrated_parser = subparsers.add_parser(
    "integrated_vec", help="Run an integrated indexer pipeline"
)
integrated_parser.set_defaults(func=integrated_vec.run_integrated_vec)
integrated_parser.add_argument(
    "--config",
    metavar="CONFIG",
    required=True,
    help="Path to the YAML configuration file.",
)
integrated_parser.add_argument(
    "--env", metavar="ENV", required=False, help="Environment file to load."
)


def run(args=None):
    args = parser.parse_args(args=args)
    parser.exit(args.func(args))
