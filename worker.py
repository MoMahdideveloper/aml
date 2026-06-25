import logging
import os
import sys

from celery_app import celery_app


def main() -> None:
    role = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CELERY_ROLE", "worker")).lower()
    app_path = "celery_app.celery_app"

    if role == "beat":
        argv = [
            "celery",
            "-A",
            app_path,
            "beat",
            "--loglevel=INFO",
        ]
    else:
        # `solo` avoids prefork issues on local Windows environments.
        argv = [
            "celery",
            "-A",
            app_path,
            "worker",
            "--loglevel=INFO",
            "--pool=solo",
        ]

    logging.info("Starting Celery %s process", role)
    celery_app.worker_main(argv)


if __name__ == "__main__":
    main()

