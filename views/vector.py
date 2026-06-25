import logging

from flask import Blueprint, jsonify, request

from vector_init import ensure_vector_database_ready, vector_initializer
from services.vector_service import vector_service
from utils.execution_tracer import log_execution


logger = logging.getLogger(__name__)

bp = Blueprint("vector_api", __name__, url_prefix="/api/vector")


@bp.route("/status", methods=["GET"])
@log_execution
def vector_status():
    """
    GET /api/vector/status
    Return diagnostic information about the vector search subsystem.
    """
    try:
        stats = vector_initializer.get_vector_database_stats()
    except Exception as exc:
        logger.error(f"Failed to collect vector database stats: {exc}")
        stats = {"error": str(exc), "database_ready": False}

    try:
        service_status = vector_service.get_status()
    except Exception as exc:
        logger.error(f"Failed to collect vector service status: {exc}")
        service_status = {"error": str(exc), "database_ready": False}

    database_ready = bool(
        stats.get("database_ready", False) and service_status.get("database_ready", False)
    )

    response = {
        "database_ready": database_ready,
        "properties_indexed": stats.get("properties_indexed", 0),
        "customers_indexed": stats.get("customers_indexed", 0),
        "vectorizer_fitted": service_status.get("vectorizer_fitted", False),
        "persist_directory": service_status.get("persist_directory"),
        "vectorizer_file_exists": service_status.get("vectorizer_file_exists", False),
        "service_status": service_status,
        "database_stats": stats,
    }

    # Optional auto-initialize when explicitly requested
    if request.args.get("init") == "1" and not database_ready:
        response["init_triggered"] = ensure_vector_database_ready()

    return jsonify(response)
