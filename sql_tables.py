import sys
import logging
import yaml
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

from meshtastic import portnums_pb2, mesh_pb2, config_pb2

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


# class Telemetry(Base):
#     pass


class Position(Base):
    __tablename__ = 'position'
    __table_args__ = {'schema': 'meshtastic'}

    uuid = sa.Column(sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('meshtastic.data.uuid'), primary_key=True)
    data = sa.orm.relationship("Data", back_populates="position", uselist=False)

    latitude_i = sa.Column(sa.Integer, nullable=True)
    longitude_i = sa.Column(sa.Integer, nullable=True)
    altitude = sa.Column(sa.Integer, nullable=True)
    time = sa.Column(sa.Integer, nullable=True)
    location_source = sa.Column(sa.String, nullable=True)
    altitude_source = sa.Column(sa.String, nullable=True)
    timestamp = sa.Column(sa.Integer, nullable=True)
    timestamp_millis_adjust = sa.Column(sa.Integer, nullable=True)
    altitude_hae = sa.Column(sa.Integer, nullable=True)
    altitude_geoidal_separation = sa.Column(sa.Integer, nullable=True)
    PDOP = sa.Column(sa.Integer, nullable=True)
    HDOP = sa.Column(sa.Integer, nullable=True)
    VDOP = sa.Column(sa.Integer, nullable=True)
    gps_accuracy = sa.Column(sa.Integer, nullable=True)
    ground_speed = sa.Column(sa.Integer, nullable=True)
    ground_track = sa.Column(sa.Integer, nullable=True)
    fix_quality = sa.Column(sa.Integer, nullable=True)
    fix_type = sa.Column(sa.Integer, nullable=True)
    sats_in_view = sa.Column(sa.Integer, nullable=True)
    sensor_id = sa.Column(sa.Integer, nullable=True)
    next_update = sa.Column(sa.Integer, nullable=True)
    seq_number = sa.Column(sa.Integer, nullable=True)
    precision_bits = sa.Column(sa.Integer, nullable=True)

    def __init__(self, position, uuid):
        self.uuid = uuid
        self.latitude_i = position.latitude_i
        self.longitude_i = position.longitude_i
        self.altitude = position.altitude
        self.time = position.time
        self.location_source = mesh_pb2.Position.LocSource.Name(position.location_source)
        self.altitude_source = mesh_pb2.Position.AltSource.Name(position.altitude_source)
        self.timestamp = position.timestamp
        self.timestamp_millis_adjust = position.timestamp_millis_adjust
        self.altitude = position.altitude
        self.altitude_geoidal_separation = position.altitude_geoidal_separation
        self.PDOP = position.PDOP
        self.HDOP = position.HDOP
        self.VDOP = position.VDOP
        self.gps_accuracy = position.gps_accuracy
        self.ground_speed = position.ground_speed
        self.ground_track = position.ground_track
        self.fix_quality = position.fix_quality
        self.fix_type = position.fix_type
        self.sats_in_view = position.sats_in_view
        self.sensor_id = position.sensor_id
        self.next_update = position.next_update
        self.seq_number = position.seq_number
        self.precision_bits = position.precision_bits

class User(Base):
    __tablename__ = 'user'
    __table_args__ = {'schema': 'meshtastic'}

    uuid = sa.Column(sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('meshtastic.data.uuid'))
    data = sa.orm.relationship("Data", back_populates="user", uselist=False)
    id = sa.Column(sa.String, nullable=False, primary_key=True)
    long_name = sa.Column(sa.String, nullable=False)
    short_name = sa.Column(sa.String, nullable=False)
    macaddr = sa.Column(sa.String, nullable=False)
    hw_model = sa.Column(sa.String, nullable=True)
    is_licensed = sa.Column(sa.Boolean, nullable=True)
    role = sa.Column(sa.String, nullable=True)
    public_key = sa.Column(sa.LargeBinary, nullable=True)

    def __init__(self, user, uuid):
        self.update(user, uuid)

    def update(self, user, uuid):
        self.uuid = uuid
        self.id = user.id
        self.long_name = user.long_name
        self.short_name = user.short_name
        self.macaddr = user.macaddr
        self.hw_model = mesh_pb2.HardwareModel.Name(user.hw_model)
        self.is_licensed = user.is_licensed
        self.role = config_pb2.Config.DeviceConfig.Role.Name(user.role)
        self.public_key = user.public_key


class Data(Base):
    __tablename__ = 'data'
    __table_args__ = {'schema': 'meshtastic'}

    uuid = sa.Column(sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('meshtastic.mesh_packet.uuid'), primary_key=True)
    mesh_packet = sa.orm.relationship("MeshPacket", back_populates="decoded", uselist=False)
    portnum = sa.Column(sa.String(32), nullable=False)
    payload = sa.Column(sa.LargeBinary, nullable=False)
    want_response = sa.Column(sa.Boolean, nullable=True)
    dest = sa.Column(sa.BigInteger, nullable=True)
    source = sa.Column(sa.BigInteger, nullable=True)
    request_id = sa.Column(sa.BigInteger, nullable=True)
    reply_id = sa.Column(sa.BigInteger, nullable=True)
    emoji = sa.Column(sa.BigInteger, nullable=True)
    bitfield = sa.Column(sa.BigInteger, nullable=True)
    user = sa.orm.relationship("User", back_populates="data", uselist=False, cascade="all, delete-orphan")
    position = sa.orm.relationship("Position", back_populates="data", uselist=False, cascade="all, delete-orphan")

    def __init__(self, data, uuid, session):
        self.uuid = uuid
        self.portnum = portnums_pb2.PortNum.Name(data.portnum)
        self.payload = data.payload
        self.want_response = data.want_response
        self.dest = data.dest
        self.source = data.source
        self.request_id = data.request_id
        self.reply_id = data.reply_id
        self.emoji = data.emoji
        self.bitfield = data.bitfield

        if self.portnum == 'NODEINFO_APP':
            user = mesh_pb2.User()
            user.ParseFromString(data.payload)
            user_from_db = session.get(User, user.id)
            if user_from_db:
                logger.info(f'User {user.id} known, updating.')
                user_from_db.update(user, self.uuid)
                self.user = user_from_db
            else:
                self.user = User(user, self.uuid)
                logger.info(f'New user {user.id} found.')

        if self.portnum == 'POSITION_APP':
            position = mesh_pb2.Position()
            position.ParseFromString(data.payload)
            self.position = Position(position, self.uuid)


class MeshPacket(Base):
    __tablename__ = 'mesh_packet'
    __table_args__ = {'schema': 'meshtastic'}

    uuid = sa.Column(sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rx_time = sa.Column(sa.BigInteger, nullable=False)
    id = sa.Column(sa.BigInteger, nullable=False)
    _from = sa.Column(sa.BigInteger, nullable=False)
    to = sa.Column(sa.BigInteger, nullable=False)
    channel = sa.Column(sa.BigInteger, nullable=True)
    decoded = sa.orm.relationship("Data", back_populates="mesh_packet", uselist=False, cascade="all, delete-orphan")
    encrypted = sa.Column(sa.LargeBinary, nullable=True)
    rx_snr = sa.Column(sa.Double, nullable=True)
    hop_limit = sa.Column(sa.BigInteger, nullable=True)
    want_ack = sa.Column(sa.Boolean, nullable=True)
    priority = sa.Column(sa.String(32), nullable=True)
    rx_rssi = sa.Column(sa.BigInteger, nullable=True)
    delayed = sa.Column(sa.BigInteger, nullable=True)
    hop_start = sa.Column(sa.Integer, nullable=True)
    public_key = sa.Column(sa.LargeBinary, nullable=True)
    pki_encrypted = sa.Column(sa.Boolean, nullable=True)

    def __init__(self, mesh_packet, session):
        self.rx_time = mesh_packet.rx_time
        self.id = mesh_packet.id
        self._from  =  mesh_packet.__getattribute__('from')
        self.to  =  mesh_packet.to
        self.channel  =  mesh_packet.channel
        self.decoded  =  Data(mesh_packet.decoded, self.uuid, session) if mesh_packet.decoded.portnum > 0 else None
        self.encrypted  =  mesh_packet.encrypted
        self.rx_snr  =  mesh_packet.rx_snr
        self.hop_limit  =  mesh_packet.hop_limit
        self.want_ack  =  mesh_packet.want_ack
        self.priority  =  mesh_pb2.MeshPacket.Priority.Name(mesh_packet.priority)
        self.rx_rssi  =  mesh_packet.rx_rssi
        self.delayed  =  mesh_packet.delayed
        self.hop_start  =  mesh_packet.hop_start
        self.public_key  =  mesh_packet.public_key
        self.pki_encrypted  =  mesh_packet.pki_encrypted


# Create the table in the database
Base.metadata.create_all(engine)