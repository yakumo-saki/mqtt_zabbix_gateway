#!/usr/bin/env python3
# coding=utf-8

import paho.mqtt.client as mqtt

from logging import getLogger, basicConfig, StreamHandler, Formatter, DEBUG, INFO, WARN
from logging import config as loggerConfig

from pprint import pprint

handler_format = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')

stream_handler = StreamHandler()
stream_handler.setFormatter(handler_format)

loggerConfig.fileConfig('logging.conf', disable_existing_loggers=False)
logger = getLogger(__name__)

#
config = None
convert = None
sender = None


def on_connect(client, userdata, flags, respons_code):
    logger.info('connect status {0}'.format(respons_code))

    topics = []
    for conv in convert:
        topic = conv["topic"]
        if (topic in topics):
            pass
        else:
            topics.append(topic)

    for topic in topics:
        logger.info("subscribe topic " + topic)
        client.subscribe(topic)


def on_message(client, userdata, msg):
    payload = str(msg.payload)
    logger.debug("received {0} {1}".format(msg.topic,str(payload)))

    settings = get_convert_settings(msg.topic)

    if settings.count == 0:
        logger.warn("[BUG] No matching convert setting: topic = {0} value = {1}".format(
            msg.topic, payload))
        return

    value = parse_value(payload)

    for setting in settings:
        if (setting["type"] == "dump"):
            logger.info("[DUMP] topic = {0} value = {1} parsed_value={2}".format(
                msg.topic, payload, value))
            continue
        elif (setting["type"] == "log"):
            out_logger = getLogger(setting["logger"])
            out_logger.info("[LOG] topic = {0} value = {1} parsed_value={2}".format(
                msg.topic, payload, value))
            continue
        elif (setting["type"] == "zabbix"):
            import subprocess
            try:
                cmd = []
                cmd.append(config["server"]["zabbix"]["sender"])
                cmd.append("-v")
                cmd.append("-z")
                cmd.append(config["server"]["zabbix"]["host"])
                cmd.append("-s")
                cmd.append(setting["zabbix_host"])
                cmd.append("-k")
                cmd.append(setting["zabbix_key"])
                cmd.append("-o")
                cmd.append(str(value))

                res = subprocess.run(cmd, stdout=subprocess.PIPE)
                logger.info("{0}:{1} value={2} sent. rc={3}".format(
                    setting["zabbix_host"],
                    setting["zabbix_key"],
                    value, res.returncode))
            except Exception as e:
                print("Error.")
                pprint(e)

            continue
        else:
            logger.warn("unknown type => " + setting["type"])
            continue


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


def get_convert_settings(topic):
    settings = []
    for conv in convert:
        if topic == conv["topic"]:
            settings.append(conv)

    return settings


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
                # pprint(logger_dict)
                loggerConfig.dictConfig(logger_dict)
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
