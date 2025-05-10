import sys
import logging

import yaml
import paho.mqtt.client as mqtt
from meshtastic import mqtt_pb2

from sqlalchemy.orm import sessionmaker



# init logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)


# load local modules after logging was initialized
from meshtastic_functions import transform_key, decrypter_factory
from sql_tables import engine, MeshPacket


# init database
Session = sessionmaker(bind=engine)


# load settings
settings = yaml.safe_load(open('settings.yml'))


# mqtt callbacks
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    client.subscribe("meshtastic/#")


def on_message(decrypter):
    def handle_message(client, userdata, msg):
        if msg.topic.startswith('meshtastic/2/e'):
            service_envelope = mqtt_pb2.ServiceEnvelope()
            service_envelope.ParseFromString(msg.payload)
            mesh_packet = service_envelope.packet
            logger.info('---------------     received packet    ---------------')
            decrypted_packet = decrypter(mesh_packet)
            session = Session()
            session.add(MeshPacket(decrypted_packet, session))
            session.commit()
            session.close()
            logger.info(mesh_packet)
    return handle_message


# init meshtastic functions
decrypter = decrypter_factory(transform_key(settings['meshtastic']['channel_keys']))

# init mqtt
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message(decrypter)
mqttc.username_pw_set(settings['mqtt']['username'], settings['mqtt']['password'])
mqttc.connect(settings['mqtt']['server'], settings['mqtt']['port'], 60)

# loop forever
mqttc.loop_forever()