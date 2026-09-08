from django.urls import path
from ninja import Schema
from ninja_extra import ControllerBase, NinjaExtraAPI, api_controller, http_get

from sirenity import siren_pagination


class Article(Schema):
    id: str
    title: str


class ArticlePage(Schema):
    items: list[Article]
    has_more: bool
    next_offset: int
    limit: int


@api_controller("/api/articles")
class ArticleController(ControllerBase):
    @siren_pagination(
        http_get,
        response=ArticlePage,
        operation_id="list_articles",
        continuation={"offset": "next_offset", "limit": "limit"},
        summary="List articles",
        description="List one page of articles.",
    )
    def list_articles(self, offset: int = 0, limit: int = 2):
        return {
            "items": [{"id": f"article-{offset + 1}", "title": "Article"}],
            "has_more": offset == 0,
            "next_offset": offset + limit,
            "limit": limit,
        }


api = NinjaExtraAPI(title="Pagination", version="1", urls_namespace="sirenity_pagination_ninja_extra")
api.register_controllers(ArticleController)

urlpatterns = [path("", api.urls)]
