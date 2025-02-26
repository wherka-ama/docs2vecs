import os
from pathlib import Path

import yaml
from cerberus import Validator


class Config:
    def __init__(self, config_file, config_schema):
        self.config_file = config_file
        self.config_schema = config_schema
        self.config = None
        self._error = None
        self._read_config()
        self._validate_config()
        if self._error:
            raise ValueError(self._error)

    def _replace_env_vars(self, data):
        if isinstance(data, str):
            if data.startswith("env."):
                # replace env. prefix with actual env var
                return os.getenv(data[4:], data)
            return data

        if isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]

        if isinstance(data, dict):
            return {key: self._replace_env_vars(value) for key, value in data.items()}

        return data

    def _read_config(self):
        with Path(self.config_file).expanduser().resolve().open() as f:
            self.config = yaml.safe_load(f)
            self.config = self._replace_env_vars(self.config)

    def _validate_config(self):
        schema = ""
        schema_file = self.config_schema
        with Path(schema_file).expanduser().resolve().open() as f:
            schema = yaml.safe_load(f)
        v = Validator(schema)
        if not v.validate(self.config):
            raise ValueError(f"Config validation errors: {v.errors}")

    def is_valid(self):
        return not self._error

    def get_data_source_config_dict(self):
        return self.config["indexer"]["data_source"]["params"]

    def get_skills_config_dict(self):
        skillset = self.config["indexer"]["skillset"]
        yield from skillset

    def get_tracker_config_dict(self):
        return (
            self.config["indexer"]["tracker"]
            if "tracker" in self.config["indexer"]
            else None
        )
