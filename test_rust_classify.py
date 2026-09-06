#!/usr/bin/env python3
import unittest

from scapy.layers.l2 import Ether, ARP
from scapy.layers.inet import IP, UDP
from scapy.utils import wrpcap

from framework import VppTestCase
from asfframework import VppTestRunner


class TestRustClassify(VppTestCase):
    """Rust Classify Node Test Case"""

    @classmethod
    def setUpClass(cls):
        super(TestRustClassify, cls).setUpClass()

        cls.create_pg_interfaces(range(1))
        for i in cls.pg_interfaces:
            i.admin_up()
            i.config_ip4()
            i.resolve_arp()

    @classmethod
    def tearDownClass(cls):
        super(TestRustClassify, cls).tearDownClass()

    def setUp(self):
        super(TestRustClassify, self).setUp()

    def test_rust_classify(self):
        """Test rust-classify with valid and malformed packets"""

        # Use auto-generated addresses from the test framework
        mac_src = self.pg0.remote_mac
        mac_dst = self.pg0.local_mac
        ip_src = self.pg0.remote_ip4
        ip_dst = self.pg0.local_ip4

        # 1. Valid packet (Expected: Forwarded)
        p_valid = (
            Ether(src=mac_src, dst=mac_dst)
            / IP(src=ip_src, dst=ip_dst)
            / UDP(sport=1234, dport=5678)
            / b"ValidPayload"
        )

        # 2. IPv4 with Options (Expected: Forwarded)
        p_opt = (
            Ether(src=mac_src, dst=mac_dst)
            / IP(src=ip_src, dst=ip_dst, options=b"\x01\x01\x01\x00")
            / UDP(sport=1234, dport=5678)
            / b"OptsPayload"
        )

        # 3. Invalid EtherType (ARP) (Expected: Dropped)
        p_arp = Ether(src=mac_src, dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_dst)

        # 4. Truncated packet (Expected: Dropped)
        p_trunc = (
            Ether(src=mac_src, dst=mac_dst)
            / IP(src=ip_src, dst=ip_dst, len=100)
            / UDP(sport=1234, dport=5678, len=80)
            / b"Short"
        )

        # 5. Invalid IP version (Expected: Dropped)
        p_bad_ver = (
            Ether(src=mac_src, dst=mac_dst)
            / IP(src=ip_src, dst=ip_dst, version=5)
            / UDP(sport=1234, dport=5678)
            / b"BadVersion"
        )

        # 6. Invalid header length (IHL < 5) (Expected: Dropped)
        p_bad_ihl = (
            Ether(src=mac_src, dst=mac_dst)
            / IP(src=ip_src, dst=ip_dst, ihl=4)
            / UDP(sport=1234, dport=5678)
            / b"BadIHL"
        )

        pkts = [p_valid, p_opt, p_arp, p_trunc, p_bad_ver, p_bad_ihl]

        # Save packets to a pcap file
        pcap_file = f"{self.tempdir}/rust_test.pcap"
        wrpcap(pcap_file, pkts)

        # Read initial error counters
        start_valid = sum(
            self.statistics.get_counter(
                "/err/rust-classify/valid udp packets forwarded"
            )
        )
        start_malf = sum(
            self.statistics.get_counter("/err/rust-classify/malformed packets dropped")
        )
        # Generate traffic using VPP CLI
        self.vapi.cli(
            f"packet-generator new {{ name rust_test node rust-classify pcap {pcap_file} }}"
        )
        self.vapi.cli("packet-generator enable")

        # Check results: 2 valid forwarded, 4 malformed dropped
        end_valid = sum(
            self.statistics.get_counter(
                "/err/rust-classify/valid udp packets forwarded"
            )
        )
        end_malf = sum(
            self.statistics.get_counter("/err/rust-classify/malformed packets dropped")
        )
        self.assertEqual(end_valid - start_valid, 2)
        self.assertEqual(end_malf - start_malf, 4)


if __name__ == "__main__":
    unittest.main(testRunner=VppTestRunner)
