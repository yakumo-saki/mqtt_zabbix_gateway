import unittest
import sys
sys.path.append("../")
from mqtt_zabbix_gateway import *


class TestMain(unittest.TestCase):
    """test class of mqtt_zabbix_gateway.py
    """

    def test_parse_value(self):
        """test method for mqtt_zabbix_gateway.py
        """
        self.assertEqual(1234.567, parse_value("b'1234.567'"))
        self.assertEqual(1234, parse_value("b'1234'"))
        self.assertEqual("abcd", parse_value("b'abcd'"))


if __name__ == "__main__":
    unittest.main()
