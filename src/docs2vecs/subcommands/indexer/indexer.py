from pathlib import Path

from dotenv import load_dotenv

from docs2vecs.subcommands.indexer import config as cfg_module
from docs2vecs.subcommands.indexer.config import Config
from docs2vecs.subcommands.indexer.skills.factory import SkillFactory


class Indexer:
    def __init__(self, config: Config):
        self._config = config

    def run(self):
        output = None
        for skill_config_dict in self._config.get_skills_config_dict():
            skill = SkillFactory.get_skill(skill_config_dict, self._config)
            output = skill.run(output)


def does_file_exist(file_path: str) -> bool:
    file_path = Path(file_path).expanduser().resolve()
    return file_path.exists()


def run_indexer(args):
    if args.env and not does_file_exist(args.env):
        print(f"Error: env file '{args.env}' does not exist!")
        return 1

    if args.config and not does_file_exist(args.config):
        print(f"Error: config file '{args.config}' does not exist!")
        return 1

    if args.env:
        load_dotenv(args.env)

    config_schema = Path(cfg_module.__file__).parent / "config_schema.yaml"
    config = Config(args.config, config_schema)
    indexer = Indexer(config)
    indexer.run()
