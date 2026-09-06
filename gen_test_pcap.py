"""
Generates traffic.pcap with 4 packets - one for
each case that network_parser::parse_packet must distinguish:
  p1 - valid Ethernet+IPv4+UDP -> is_valid=1, dest_port=5678
  p2 - IPv4 with options (IHL=6, 24-byte header instead of 20)
       -> is_valid=1, the parser must correctly skip the options
  p3 - Ethernet with EtherType=ARP (0x0806) instead of IPv4 (0x0800)
       -> is_valid=0, error_code = CPARSE_INVALID_ETHER_TYPE (3)
  p4 - valid packet with a physically truncated payload;
       the UDP header still claims "I have X bytes", but there are
       fewer bytes in the buffer -> is_valid=0, error_code = CPARSE_INVALID_UDP_LENGTH (7)

Usage:
  python3 gen_test_pcap.py
  packet-generator new { name pcap_test node rust-classify pcap traffic.pcap }
  packet-generator enable
  show trace
"""

from scapy.all import Ether, IP, UDP, ARP, IPOption, raw, wrpcap

p1 = (
    Ether(src="00:11:22:33:44:55", dst="00:aa:bb:cc:dd:ee")
    / IP(src="10.0.0.1", dst="10.0.0.2")
    / UDP(sport=1234, dport=5678)
    / b"ValidPayload"
)

p2 = (
    Ether(src="00:11:22:33:44:55", dst="00:aa:bb:cc:dd:ee")
    / IP(src="10.0.0.1", dst="10.0.0.2", options=[IPOption(b"\x00\x00\x00\x00")])
    / UDP(sport=1234, dport=5678)
    / b"OptsPayload"
)

p3 = Ether(src="00:11:22:33:44:55", dst="ff:ff:ff:ff:ff:ff") / ARP(pdst="10.0.0.2")

base_pkt = (
    Ether(src="00:11:22:33:44:55", dst="00:aa:bb:cc:dd:ee")
    / IP(src="10.0.0.1", dst="10.0.0.2")
    / UDP(sport=1234, dport=5678)
    / b"TruncatedData12345"
)
p4 = Ether(raw(base_pkt)[:-15])

print("Generating traffic.pcap...")
wrpcap("traffic.pcap", [p1, p2, p3, p4])
print("Done!")
