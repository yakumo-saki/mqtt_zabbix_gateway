#!/usr/bin/env python3

import paho.mqtt.client as mqtt

from logging import getLogger, basicConfig, StreamHandler, Formatter, DEBUG, INFO, WARN
from logging import config as loggerConfig

import pprint

handler_format = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')

#basicConfig(level=DEBUG)
stream_handler = StreamHandler()
stream_handler.setFormatter(handler_format)

loggerConfig.fileConfig('logging.conf', disable_existing_loggers=False)
logger = getLogger(__name__)
#logger.setLevel(DEBUG)
#logger.addHandler(stream_handler)

#
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

    if (setting["type"] == "log"):
        out_logger = getLogger(setting["logger"])
        out_logger.info("[LOG] topic = {0} value = {1} parsed_value={2}".format(
            msg.topic, payload, value))
        return

    if (setting["type"] == "zabbix"):
        from pyzabbix import ZabbixMetric, ZabbixSender
        # zabbix
        zbx_host = config["server"]["zabbix"]["host"]
        zbx_port = config["server"]["zabbix"]["port"]
        sender = ZabbixSender(zbx_host, zbx_port)
        packet = []
        packet.append(ZabbixMetric(setting["zabbix_host"], setting["zabbix_key"], value))
        logger.debug(str(packet))
        result = sender.send(packet)
        print(result)
        logger.info("zabbix send result {0}".format(str(result)))
        return


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


def get_config(filename):
    # get config
    import yaml
    with open(filename, 'r') as yaml_file:
        # ファイルの中身を辞書として取得する
        conf = yaml.load(yaml_file)

    return conf


def load_logger_config():
    for conv in convert:
        if "log" == conv["type"]:
            if "config" in conv:
                logger.info("loading logger config: %s", conv["config"])
                logger_dict = get_config(conv["config"])
                pprint.pprint(logger_dict)
                loggerConfig.dictConfig(logger_dict)
                # loggerConfig.fileConfig(conv["config"], None, False)
            else:
                logger.debug("No config. skip loading logger config")



def load_logger_config_old():
    for conv in convert:
        if "log" == conv["type"]:
            logger.info("loading logger config: %s", conv["config"])
            loggerConfig.fileConfig(conv["config"], None, False)


if __name__ == '__main__':

    config = get_config('config.yaml')

    # mqtt
    mq_host = config["server"]["mqtt"]["host"]
    mq_port = config["server"]["mqtt"]["port"]

    convert = config["convert"]
    logger.debug(convert)

    load_logger_config()

    client = mqtt.Client(protocol=mqtt.MQTTv311)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(host=mq_host, port=mq_port, keepalive=60)

    # 待ち受け状態にする
    client.loop_forever()
