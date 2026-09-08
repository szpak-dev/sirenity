from django.urls import path
from ninja import NinjaAPI, Schema

from sirenity import siren_pagination


class Article(Schema):
    id: str
    title: str


class ArticlePage(Schema):
    items: list[Article]
    has_more: bool
    next_offset: int
    limit: int


api = NinjaAPI(title="Pagination", version="1", urls_namespace="sirenity_pagination_ninja")


@siren_pagination(
    api.get,
    "/api/articles",
    response=ArticlePage,
    operation_id="list_articles",
    continuation={"offset": "next_offset", "limit": "limit"},
    summary="List articles",
    description="List one page of articles.",
)
def list_articles(request, offset: int = 0, limit: int = 2):
    return {
        "items": [{"id": f"article-{offset + 1}", "title": "Article"}],
        "has_more": offset == 0,
        "next_offset": offset + limit,
        "limit": limit,
    }


urlpatterns = [path("", api.urls)]
