import logging
import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from meshtastic import protocols, mesh_pb2, portnums_pb2, KnownProtocol
import google.protobuf.json_format
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from sql_tables import engine, MeshPacket, Node

# init logging
logger = logging.getLogger(__name__)


# init database
Session = sessionmaker(bind=engine)


def on_mesh_packet_receive(mesh_packet):
    assert isinstance(mesh_packet.encrypted, bytes), f"Expected bytes, but got {type(mesh_packet.encrypted)}"

    session = Session()

    session.add(
        MeshPacket(
            rx_time=mesh_packet.rx_time,
            id=mesh_packet.id,
            _from = mesh_packet.__getattribute__('from'),
            to = mesh_packet.to,
            channel = mesh_packet.channel,
            #decoded = mesh_packet.decoded,
            encrypted = mesh_packet.encrypted,
            rx_snr = mesh_packet.rx_snr,
            hop_limit = mesh_packet.hop_limit,
            want_ack = mesh_packet.want_ack,
            priority = mesh_packet.priority,
            rx_rssi = mesh_packet.rx_rssi,
            delayed = mesh_packet.delayed,
            hop_start = mesh_packet.hop_start,
            public_key = mesh_packet.public_key,
            pki_encrypted = mesh_packet.pki_encrypted
        )
    )
    session.commit()
    session.close()


def on_text_receive(mesh_packet_dict):
    try:
        asBytes = mesh_packet_dict['decoded']['payload']
        mesh_packet_dict['decoded']['text'] = base64.b64decode(asBytes).decode('utf-8')
    except Exception as e:
        logger.error(f'Malformatted utf8 in text message: {e}')

    return mesh_packet_dict


def on_nodeinfo_receive(mesh_packet_dict):
    session = Session()

    node_data = mesh_packet_dict['decoded'][protocols[portnums_pb2.NODEINFO_APP].name]
    node_data['id'] = int(node_data['id'][1:], 16)
    stmt = insert(Node).values(**node_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={col: getattr(stmt.excluded, col) for col in node_data if col != 'id'}
    )
    session.execute(stmt)
    session.commit()
    session.close()

    return mesh_packet_dict


# add some handlers for specific portnums (this is taken care of in meshtastic python package but not independent from interface)
for portnum in protocols.keys():
    protocols[portnum] = KnownProtocol(
        name=protocols[portnum].name,
        protobufFactory=protocols[portnum].protobufFactory,
        onReceive=None  # remove all onReveive callbacks
    )

protocols[portnums_pb2.TEXT_MESSAGE_APP] = KnownProtocol(
    name=protocols[portnums_pb2.TEXT_MESSAGE_APP].name,
    protobufFactory=protocols[portnums_pb2.TEXT_MESSAGE_APP].protobufFactory,
    onReceive=on_text_receive
)

protocols[portnums_pb2.NODEINFO_APP] = KnownProtocol(
    name=protocols[portnums_pb2.NODEINFO_APP].name,
    protobufFactory=protocols[portnums_pb2.NODEINFO_APP].protobufFactory,
    onReceive=on_nodeinfo_receive
)


def transform_key(raw_keys=['1PG7OiApB1nwvP+rz05pAQ==']):
    def transform_single_key(raw_key):
        padded_key = raw_key.ljust(len(raw_key) + ((4 - (len(raw_key) % 4)) % 4), '=')
        replaced_key = padded_key.replace('-', '+').replace('_', '/')
        key_bytes = base64.b64decode(replaced_key.encode('ascii'))
        return key_bytes
    return [transform_single_key(raw_key) for raw_key in raw_keys]


def decrypter_factory(key_bytes_list):
    def decrypt_payload(mesh_packet):
        for key_bytes in key_bytes_list:
            # Extract the nonce from the packet
            nonce_packet_id = getattr(mesh_packet, 'id').to_bytes(8, 'little')
            nonce_from_node = getattr(mesh_packet, 'from').to_bytes(8, 'little')
            nonce = nonce_packet_id + nonce_from_node

            # Decrypt the message
            cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(nonce), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_bytes = decryptor.update(getattr(mesh_packet, 'encrypted')) + decryptor.finalize()

            # Parse the decrypted message
            try:
                data = mesh_pb2.Data()
                data.ParseFromString(decrypted_bytes)

                mesh_packet.decoded.CopyFrom(data)

                return mesh_packet
            except:
                pass
        
        logger.info('Could not decrypt packet.')
        return None

    return decrypt_payload


def parse_packet(mesh_packet):
    portnum = mesh_packet.decoded.portnum
    mesh_packet_dict = google.protobuf.json_format.MessageToDict(mesh_packet)
    try:
        protocol_decoder = protocols[portnum]
    except KeyError:
        logger.warning(f'Unknown portnum {portnum}')
        return mesh_packet_dict

    if protocol_decoder.protobufFactory:
        pb = protocol_decoder.protobufFactory() 
        pb.ParseFromString(mesh_packet.decoded.payload)
        p = google.protobuf.json_format.MessageToDict(pb)
        mesh_packet_dict['decoded'][protocol_decoder.name] = p

    if protocol_decoder.onReceive:
        mesh_packet_dict = protocol_decoder.onReceive(mesh_packet_dict)
    return mesh_packet_dict