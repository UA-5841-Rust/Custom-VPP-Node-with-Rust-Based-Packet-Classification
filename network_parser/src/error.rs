#[derive(Debug, PartialEq)]
#[repr(u32)]
pub enum ParseError {
    PacketTooShort,
    InvalidEtherType,
    InvalidIpv4Version,
    InvalidIpv4HeaderLength,
    InvalidIpv4TotalLength,
    InvalidUdpLength,
    UnsupportedProtocol,
}
