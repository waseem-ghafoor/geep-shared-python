from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

SessionLocal: sessionmaker[Session]
