import logging
import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from meshtastic import protocols, mesh_pb2

# init logging
logger = logging.getLogger(__name__)


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
        return mesh_packet

    return decrypt_payload