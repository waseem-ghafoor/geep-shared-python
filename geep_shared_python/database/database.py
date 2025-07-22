import boto3
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from geep_shared_python.schemas.shared_schemas import SharedSettings

settings = SharedSettings()

if settings.environment == "local" or settings.environment == "ci":
    database_url = (
        f"postgresql://{settings.db_user}:{settings.db_password}@"
        + f"{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )

    engine = create_engine(database_url)
else:
    # we are running in kube on AWS
    # token (password) set by the event trigger below
    database_url = (
        f"postgresql://{settings.db_user}@{settings.db_host}/{settings.db_name}"
    )

    engine = create_engine(
        database_url,
        pool_recycle=300,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"},
    )

    @event.listens_for(engine, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):  # type: ignore
        client = boto3.client("rds")  # type: ignore
        token = client.generate_db_auth_token(  # type: ignore
            DBHostname=settings.db_host,
            Port=settings.db_port,
            DBUsername=settings.db_user,
            Region=settings.aws_region,
        )  # type: ignore

        # refresh token
        cparams["password"] = token


# global SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
