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


missing_query_api = NinjaAPI(
    title="Missing query",
    version="1",
    urls_namespace="sirenity_pagination_missing_query",
)


@siren_pagination(
    missing_query_api.get,
    "/api/articles",
    response=ArticlePage,
    operation_id="list_articles",
    continuation={"cursor": "next_offset"},
    summary="List articles",
    description="List one page of articles.",
)
def list_articles_without_cursor(request, offset: int = 0):
    return {"items": [], "has_more": False, "next_offset": offset, "limit": 2}


missing_response_api = NinjaAPI(
    title="Missing response",
    version="1",
    urls_namespace="sirenity_pagination_missing_response",
)


@siren_pagination(
    missing_response_api.get,
    "/api/articles",
    response=ArticlePage,
    operation_id="list_articles",
    continuation={"offset": "missing"},
    summary="List articles",
    description="List one page of articles.",
)
def list_articles_without_response_property(request, offset: int = 0):
    return {"items": [], "has_more": False, "next_offset": offset, "limit": 2}


duplicate_status_api = NinjaAPI(
    title="Duplicate status",
    version="1",
    urls_namespace="sirenity_pagination_duplicate_status",
)


@duplicate_status_api.get(
    "/api/articles",
    response={200: ArticlePage},
    operation_id="list_articles",
    summary="List articles",
    description="List one page of articles.",
    openapi_extra={
        "responses": {
            "200": {
                "links": {
                    "next": {
                        "operationId": "list_articles",
                        "parameters": {"offset": "$response.body#/next_offset"},
                    }
                }
            }
        }
    },
)
def list_articles_with_duplicate_status(request, offset: int = 0):
    return {"items": [], "has_more": False, "next_offset": offset, "limit": 2}


urlpatterns = [
    path("missing-query/", missing_query_api.urls),
    path("missing-response/", missing_response_api.urls),
    path("duplicate-status/", duplicate_status_api.urls),
]
