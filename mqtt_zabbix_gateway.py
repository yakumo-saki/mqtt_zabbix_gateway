#!/usr/bin/env python3

import paho.mqtt.client as mqtt
from pyzabbix import ZabbixMetric, ZabbixSender

from logging import getLogger, basicConfig, StreamHandler, Formatter, DEBUG, INFO, WARN
handler_format = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')

#basicConfig(level=DEBUG)
stream_handler = StreamHandler()
stream_handler.setFormatter(handler_format)

logger = getLogger(__name__)
logger.setLevel(DEBUG)
logger.addHandler(stream_handler)

config = None

convert = None

sender = None


def on_connect(client, userdata, flags, respons_code):
    logger.info('connect status {0}'.format(respons_code))

    for conv in convert:
        topic = conv["topic"]
        logger.info("subscribe topic " + topic)
        client.subscribe(topic)


def on_message(client, userdata, msg):
    payload = str(msg.payload)
    logger.debug("received {0} {1}".format(msg.topic,str(payload)))

    setting = get_convert_setting(msg.topic)

    # logger.debug(setting)

    if setting == None:
        logger.warn("[BUG] No matching convert setting: topic = {0} value = {1}".format(
            msg.topic, payload))
        return

    value = parse_value(payload)

    if (setting["type"] == "dump"):
        logger.info("[DUMP] topic = {0} value = {1} parsed_value={2}".format(
            msg.topic, payload, value))
        return

    if (setting["type"] == "zabbix"):
        packet = []
        packet.append(ZabbixMetric(setting["zabbix_host"], setting["zabbix_key"], value))
        logger.debug(str(packet))
        result = sender.send(packet)
        logger.debug("zabbix send result {0}".format(str(result)))


def parse_value(value):
    # b'1234.56' を想定している
    v = value
    if value.startswith("b'"):
        v = (value[2:])[:-1]  # b'' を削除したい

    try:
        return int(v)
    except ValueError:
        # logger.debug("Not int " + v)
        pass

    try:
        return float(v)
    except ValueError:
        #logger.debug("NOT FLOAT " + v)
        pass

    return v


def get_convert_setting(topic):
    for conv in convert:
        if topic == conv["topic"]:
            # logger.debug("match")
            return conv

    return None


def get_config():
    # get config
    import yaml
    with open('config.yaml', 'r') as yaml_file:
        # ファイルの中身を辞書として取得する
        conf = yaml.load(yaml_file)

    return conf


if __name__ == '__main__':

    config = get_config()

    # zabbix
    zbx_host = config["server"]["zabbix"]["host"]
    zbx_port = config["server"]["zabbix"]["port"]
    sender = ZabbixSender(zbx_host, zbx_port)

    # mqtt
    mq_host = config["server"]["mqtt"]["host"]
    mq_port = config["server"]["mqtt"]["port"]

    convert = config["convert"]
    logger.debug(convert)

    client = mqtt.Client(protocol=mqtt.MQTTv311)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(host=mq_host, port=mq_port, keepalive=60)

    # 待ち受け状態にする
    client.loop_forever()
