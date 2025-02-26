import json
import time
from pathlib import Path
from typing import IO, List, Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from docs2vecs.subcommands.indexer.config import Config
from docs2vecs.subcommands.indexer.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class ScrollWorldExporterSkill(IndexerSkill):
    def __init__(self, config: dict, global_config: Config) -> None:
        super().__init__(config, global_config)
        self._auth_header = f"Bearer {self._config['auth_token']}"
        self._api_url = self._config["api_url"]
        self._export_folder = Path(self._config["export_folder"]).expanduser().resolve()
        self._confluence_prefix = self._config["confluence_prefix"]
        self._confluence_prefix = "https://amadeus.atlassian.net/wiki"

    def _start_export(self, page_id: str, api_url: str, auth_header: str) -> str:
        EXPORT_PARAMETERS = {
            "pageId": page_id,
            "templateId": "com.k15t.scroll.office.default-template-2",
            "scope": (
                self._config["scope"] if "scope" in self._config else "current"
            ),  # current - for current, descendants - for current + descendants
            "locale": "en-US",
            "versionId": "string",
            "variantId": "string",
            "languageKey": "string",
        }

        data: bytes = json.dumps(EXPORT_PARAMETERS).encode("utf-8")
        headers: dict = {
            "Content-Type": "application/json",
            "Authorization": auth_header,
        }
        if not api_url.lower().startswith(("http:", "https:")):
            raise ValueError("API URL must start with http:// or https:")
        response = urlopen(Request(api_url, data, headers, method="POST"))  # noqa: S310
        return json.load(response)["jobId"]

    def _get_status(self, job_id: str):
        url: str = f"{self._api_url}/{job_id}/status"
        headers: dict = {"Authorization": self._auth_header}
        if not url.lower().startswith(("http:", "https:")):
            raise ValueError("API URL must start with http:// or https:")
        response = urlopen(Request(url, None, headers, method="GET"))  # noqa: S310
        return json.load(response)

    def _get_filename(self, response) -> str:
        final_url_path = urlparse(response.url).path
        last_segment = final_url_path.split("/")[-1]
        return unquote(last_segment)

    def _download_file(self, url: str) -> str:
        headers: dict = {}
        if not url.lower().startswith(("http:", "https:")):
            raise ValueError("API URL must start with http:// or https:")
        response = urlopen(Request(url, None, headers, method="GET"))  # noqa: S310
        filename: str = self._get_filename(response)

        local_file: IO = (
            Path(f"{self._export_folder}/{filename}" or "export.data")
            .expanduser()
            .resolve()
            .open(mode="wb")
        )
        local_file.write(response.read())
        local_file.close()

        download_path = Path(local_file.name).expanduser().resolve()
        self.logger.debug(f"Stored downloaded file at: {download_path!s}")

        return str(download_path)

    def _extract_page_id_from_url(self, url: str) -> str:
        if "homepageId" in url:
            return url.split("=")[1]

        tokens = url.split("/")
        page_id = tokens[tokens.index("pages") + 1]
        return page_id

    def _extract_confluence_page_ids(self) -> List[str]:
        cp_id_list = []
        if self._config.get("page_ids"):
            cp_id_list += self._config["page_ids"]

        if self._config.get("page_urls"):
            for page_url in self._config["page_urls"]:
                cp_id_list.append(self._extract_page_id_from_url(page_url))

        return cp_id_list

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info("Running ScrollWorldExporter")

        doc_list: List[Document] = []
        page_id_to_export = self._extract_confluence_page_ids()
        for page_id in page_id_to_export:
            self.logger.debug(f"Exporting confluence page: {page_id}")
            export_job_id: str = self._start_export(
                page_id, self._api_url, self._auth_header
            )
            done: bool = False
            download_url = None
            while not done:
                time.sleep(self._config["poll_interval"])
                status = self._get_status(export_job_id)
                self.logger.debug(
                    f"Step {status['step']:d} of {status['totalSteps']:d} ({status['stepProgress']:d}%)"
                )
                print(
                    f"Step {status['step']:d} of {status['totalSteps']:d} ({status['stepProgress']:d}%)"
                )
                done = status["status"] != "incomplete"
                if done:
                    download_url = status["downloadUrl"]

            source_url = (
                f"{self._confluence_prefix}/pages/viewpage.action?pageId={page_id}"
            )
            doc_list.append(
                Document(
                    filename=self._download_file(download_url), source_url=source_url
                )
            )

        return doc_list
