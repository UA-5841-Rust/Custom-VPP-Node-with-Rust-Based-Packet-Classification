#!/usr/bin/env python3

import unittest
from framework import VppTestCase
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP, TCP
from scapy.packet import Raw


class TestRustClassify(VppTestCase):
    """ Rust Classify Plugin Test """

    @classmethod
    def setUpClass(cls):
        super(TestRustClassify, cls).setUpClass()
        cls.create_pg_interfaces(range(1))
        for i in cls.pg_interfaces:
            i.admin_up()
            i.config_ip4()
            i.resolve_arp()
        cls.vapi.cli("set interface feature %s rust-classify-node arc device-input"
                     % cls.pg0.name)

    @classmethod
    def tearDownClass(cls):
        super(TestRustClassify, cls).tearDownClass()

    def test_rust_classify_counters(self):
        p_valid = (Ether(src=self.pg0.remote_mac, dst=self.pg0.local_mac) /
                   IP(src=self.pg0.remote_ip4, dst=self.pg0.local_ip4) /
                   UDP(sport=1234, dport=5678) /
                   Raw(b'Payload'))

        p_options = (Ether(src=self.pg0.remote_mac, dst=self.pg0.local_mac) /
                     IP(src=self.pg0.remote_ip4, dst=self.pg0.local_ip4,
                        options=b'\x01\x01\x01\x00') /
                     UDP(sport=1234, dport=5678) /
                     Raw(b'Payload'))

        p_tcp = (Ether(src=self.pg0.remote_mac, dst=self.pg0.local_mac) /
                 IP(src=self.pg0.remote_ip4, dst=self.pg0.local_ip4) /
                 TCP(sport=1234, dport=5678) /
                 Raw(b'Payload'))

        p_ipv6_ethertype = (Ether(src=self.pg0.remote_mac,
                                  dst=self.pg0.local_mac, type=0x86dd) /
                            Raw(b'Garbage'))

        p_truncated = Ether(Raw(bytes(p_valid)[:30]))

        cnt_fwd = self.statistics.get_err_counter('/err/rust-classify-node/Valid UDP packets forwarded')
        cnt_malf = self.statistics.get_err_counter('/err/rust-classify-node/Malformed or too short packets')
        cnt_unsup = self.statistics.get_err_counter('/err/rust-classify-node/Unsupported protocol (not UDP)')

        self.pg0.add_stream([p_valid, p_options, p_tcp, p_ipv6_ethertype, p_truncated])
        self.pg_enable_capture(self.pg_interfaces)
        self.pg_start()

        cnt_fwd_new = self.statistics.get_err_counter('/err/rust-classify-node/Valid UDP packets forwarded')
        cnt_malf_new = self.statistics.get_err_counter('/err/rust-classify-node/Malformed or too short packets')
        cnt_unsup_new = self.statistics.get_err_counter('/err/rust-classify-node/Unsupported protocol (not UDP)')

        self.assertEqual(cnt_fwd_new - cnt_fwd, 2, "Valid packets counter mismatch")

        self.assertGreaterEqual(cnt_unsup_new - cnt_unsup, 2, "Unsupported packets counter mismatch")

        self.assertGreaterEqual(cnt_malf_new - cnt_malf, 1, "Malformed packets counter mismatch")


if __name__ == '__main__':
    unittest.main()