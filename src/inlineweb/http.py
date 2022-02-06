from collections import defaultdict
from urllib.parse import urlparse

import requests
import magic


class HTTP:
    options = defaultdict(lambda: 0)

    def __init__(self, base: str, **kwargs):
        self.base = urlparse(base)

        for k, v in kwargs.items():
            self.options[k] = v

    def get(self, url: str):
        purl = urlparse(url)

        if purl.scheme not in ["http", "https"]:
            return None

        if self.options["same_domain"] and purl.netloc != self.base.netloc:
            return None

        head = requests.head(url)
        if self.options["max_size"] and int(head.headers["content-length"]) >= self.options["max_size"]:
            return None

        get = requests.get(url)
        get.encoding = "utf-8"

        get.mime = magic.from_buffer(get.content, mime=True)
        if get.mime == "text/plain":
            get.mime = "image/svg+xml"

        return get
