#!/usr/bin/env python3

import paho.mqtt.client as mqtt
from ZabbixSender import ZabbixPacket, ZabbixSender

from logging import getLogger, basicConfig, StreamHandler, Formatter, DEBUG, INFO, WARN
from logging import config as loggerConfig

from pprint import pprint

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
    #zabbix_packets = ZabbixPacket()
    #sender = MyZabbixSender()

    for setting in settings:
        pprint(setting)

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
            #zabbix_packets.add(setting["zabbix_host"], setting["zabbix_key"], value)
            #sender.add(setting["zabbix_host"], setting["zabbix_key"], value)
            import subprocess
            try:
                exec = '{0} -v -z "{1}" -s "{2}" -k "{3}" -o "{4}"'.format(
                    config["server"]["zabbix"]["sender"],
                    config["server"]["zabbix"]["host"],
                    setting["zabbix_host"],
                    setting["zabbix_key"],
                    value)
                print("EXEC = " + exec)
                res = subprocess.check_call(exec)
                print("PROCESS END " + res)
            except:
                print("Error.")

            continue
        else:
            logger.warn("unknown type => " + setting["type"])
            continue

    sender.send()

    #zabbix_send(zabbix_packets)


def zabbix_send(packets):
    zbx_host = config["server"]["zabbix"]["host"]
    zbx_port = config["server"]["zabbix"]["port"]

    logger.debug("zabbix send")
    server = ZabbixSender(zbx_host, zbx_port)

    print(str(packets))
    logger.debug("before zabbix send")
    server.send(packets)
    logger.debug("after zabbix send")

    logger.info("zabbix send result {0}".format(str(server.status)))
    pprint(server.status)
    return


def zabbix_sender(packet):
    import socket
    import json
    import re
    import time

    zbx_host = config["server"]["zabbix"]["host"]
    zbx_port = config["server"]["zabbix"]["port"]

    print(zbx_host, zbx_port)

    print("packet")
    pprint(str(packet))

    header = b"ZBXD" + b'\x01'
    data = str(packet).encode('utf-8')
    length = "{0:x}".format(len(packet)).ljust(8,'0')
    try:
        s = socket.socket()
        s.connect((zbx_host, int(zbx_port)))
        print("CONN OK")

        data = header + str(length).encode() + data
        pprint(data)

        s.send(data)
        print("SEND OK")

        time.sleep(0.5)
        raw_ret = s.recv(2048)
        pprint(raw_ret)

        status = raw_ret.decode('utf-8')
        #status = s.recv(1024).decode('utf-8')

        print("ZBX RECV OK " + status)
        pprint(status)

        s.close()
        print("sock closed")

        re_status = re.compile('(\{.*\})')

        pprint("RE compile")

        status = re_status.search(status).groups()[0]

        pprint("re exec")

        logger.info("sent done")
        logger.info(status)

    except Exception as e:  # TODO: Horrible! Rewrite immediately.
        logger.error(e)
        raise("Can't connect zabbix server")


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
