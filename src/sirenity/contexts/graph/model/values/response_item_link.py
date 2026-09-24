from .response_link import SirenResponseLink


class SirenResponseItemLink(SirenResponseLink):
    item_collection: tuple[str, ...]
