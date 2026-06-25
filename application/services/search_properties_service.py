"""
Application service for property search use-case.
"""

from typing import Dict, Any

from infrastructure.query.property_query import build_property_search_query
from application.dtos import SearchRequest
from application.result import Success


class SearchPropertiesService:
    """Application service for searching properties."""

    def search_properties(self, search_request: SearchRequest) -> Dict[str, Any]:
        """
        Search for properties based on the search request DTO.

        Args:
            search_request: SearchRequest DTO containing search parameters

        Returns:
            Dictionary with search results and pagination info
        """
        # Build the query using the query builder
        query = build_property_search_query(search_request)

        # Handle pagination
        page = search_request.page
        per_page = search_request.per_page
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "items": pagination.items,
            "pagination": pagination,
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_prev": pagination.has_prev,
            "has_next": pagination.has_next,
            "prev_num": pagination.prev_num,
            "next_num": pagination.next_num,
        }