import sys
import logging
import yaml
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

# init logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

# load settings
settings = yaml.safe_load(open('settings.yml'))
sql_params = settings['sql']

# Create the SQLAlchemy engine
engine = sa.create_engine(
    f"postgresql+psycopg2://{sql_params['user']}:{sql_params['password']}"
    f"@{sql_params['server']}:{sql_params['port']}/{sql_params['database']}"
)

# Test the connection
with engine.connect() as connection:
    assert connection.execute(sa.text("select 1;"))

# create tables
Base = declarative_base()


class MeshPacket(Base):
    __tablename__ = 'mesh_packet'
    __table_args__ = {'schema': 'meshtastic'}

    uuid = sa.Column(sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rx_time = sa.Column(sa.BigInteger, nullable=False)
    id = sa.Column(sa.BigInteger, nullable=False)
    _from = sa.Column(sa.BigInteger, nullable=False)
    to = sa.Column(sa.BigInteger, nullable=False)
    channel = sa.Column(sa.BigInteger, nullable=True)
    decoded = sa.Column(sa.LargeBinary, nullable=True)
    encrypted = sa.Column(sa.LargeBinary, nullable=True)
    rx_snr = sa.Column(sa.Double, nullable=True)
    hop_limit = sa.Column(sa.BigInteger, nullable=True)
    want_ack = sa.Column(sa.Boolean, nullable=True)
    priority = sa.Column(sa.BigInteger, nullable=True)
    rx_rssi = sa.Column(sa.BigInteger, nullable=True)
    delayed = sa.Column(sa.BigInteger, nullable=True)
    hop_start = sa.Column(sa.Integer, nullable=True)
    public_key = sa.Column(sa.LargeBinary, nullable=True)
    pki_encrypted = sa.Column(sa.Boolean, nullable=True)


class Node(Base):
    __tablename__ = 'node'
    __table_args__ = {'schema': 'meshtastic'}

    mesh_packet_uuid = sa.Column(sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("meshtastic.mesh_packet.uuid"))
    id = sa.Column(sa.BigInteger, primary_key=True)
    longName = sa.Column(sa.String, nullable=False)
    shortName = sa.Column(sa.String, nullable=False)
    macaddr = sa.Column(sa.String, nullable=False)
    hwModel = sa.Column(sa.String, nullable=True)
    role = sa.Column(sa.String, nullable=True)
    isLicensed = sa.Column(sa.Boolean, nullable=True)
    publicKey = sa.Column(sa.String, nullable=True)

# Create the table in the database
Base.metadata.create_all(engine)