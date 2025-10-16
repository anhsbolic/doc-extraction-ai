import click
from rq import Worker

from app.services.rq_conn import get_redis_connection


@click.command()
@click.option("--queues", "-q", default="default", help="Comma separated queue names")
def main(queues: str):
    names = [q.strip() for q in queues.split(",") if q.strip()]
    if not names:
        names = ["default"]

    conn = get_redis_connection()
    print(f"🚀 RQ Worker listening on queues: {names}")
    worker = Worker(names, connection=conn)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
