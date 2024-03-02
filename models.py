import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Parameters(Base):
    __tablename__ = 'parameters'

    Number = sq.Column(sq.Integer, primary_key=True)
    ID = sq.Column(sq.String(length=10))
    Data_Length = sq.Column(sq.String(length=10))
    Length = sq.Column(sq.String(length=10))
    Name = sq.Column(sq.String(length=100))
    RusName = sq.Column(sq.String(length=100))
    Scaling = sq.Column(sq.String(length=50))
    Range = sq.Column(sq.String(length=50))
    SPN = sq.Column(sq.String(length=10))


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
