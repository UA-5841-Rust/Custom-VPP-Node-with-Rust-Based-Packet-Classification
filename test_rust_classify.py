#!/usr/bin/env python3

import unittest
from framework import VppTestCase, VppTestRunner
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP

class TestRustClassify(VppTestCase):
    """ Rust Classify Plugin Test Case """

    @classmethod
    def setUpClass(cls):
        super(TestRustClassify, cls).setUpClass()
        # Setup a single interface for testing
        cls.create_pg_interfaces(range(1))
        for i in cls.pg_interfaces:
            i.admin_up()
            i.config_ip4()
            i.resolve_arp()

    @classmethod
    def tearDownClass(cls):
        super(TestRustClassify, cls).tearDownClass()

    def test_rust_classify_counters(self):
        """ Test rust-classify-node counters with valid and invalid packets """

        # Build 3 valid UDP packets
        p_valid = (Ether(src=self.pg0.remote_mac, dst=self.pg0.local_mac) /
                   IP(src=self.pg0.remote_ip4, dst=self.pg0.local_ip4) /
                   UDP(sport=1234, dport=5678) /
                   b'Payload')

        # Build 2 invalid packets (IPv6 EtherType instead of IPv4)
        p_invalid = (Ether(src=self.pg0.remote_mac, dst=self.pg0.local_mac, type=0x86dd) /
                     b'Garbage')

        # Get baseline counter values
        err_valid = self.statistics.get_err_counter('/err/rust-classify-node/Valid UDP packets forwarded')
        err_invalid = self.statistics.get_err_counter('/err/rust-classify-node/Malformed or too short packets')

        # Inject packets into the graph (simulating pg-input)
        self.pg0.add_stream([p_valid] * 3 + [p_invalid] * 2)
        self.pg_enable_capture(self.pg_interfaces)
        self.pg_start()

        # Fetch new counter values
        err_valid_new = self.statistics.get_err_counter('/err/rust-classify-node/Valid UDP packets forwarded')
        err_invalid_new = self.statistics.get_err_counter('/err/rust-classify-node/Malformed or too short packets')

        # Verify that counters incremented correctly
        self.assertEqual(err_valid_new - err_valid, 3, "Valid packets counter mismatch")
        self.assertEqual(err_invalid_new - err_invalid, 2, "Invalid packets counter mismatch")

if __name__ == '__main__':
    unittest.main(testRunner=VppTestRunner)