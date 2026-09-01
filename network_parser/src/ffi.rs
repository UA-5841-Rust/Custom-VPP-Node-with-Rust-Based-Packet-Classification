use std::ptr;
use std::slice;

use crate::{Packet, parse_packet};
use crate::error::ParseError;

#[allow(dead_code)]
pub struct PacketHandle<'a>(Packet<'a>);

#[repr(C)]
pub struct ClassifyResult {
    pub is_valid: bool,
    pub protocol: u8,      // 0 = unknown, 1 = udp
    pub dest_port: u16,
    pub error_code: u32,   // 0 = OK, other = mapping ParseError
}

/// Mapping parsing error into u32 for C ABI
fn map_error_to_code(err: &ParseError) -> u32 {
    match err {
        ParseError::PacketTooShort => 1,
        ParseError::InvalidEtherType => 2,
        ParseError::InvalidIpv4Version => 3,
        ParseError::InvalidIpv4HeaderLength => 4,
        ParseError::InvalidIpv4TotalLength => 5,
        ParseError::InvalidUdpLength => 6,
        ParseError::UnsupportedProtocol => 7,
    }
}

/// # Safety
/// 1. `data` must be a valid pointer to a memory block of at least `len` bytes.
/// 2. The memory must not be mutated while this function runs.
/// Validation: The length is validated safely inside the Rust parser logic before accessing headers.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn packet_classify(data: *const u8, len: usize) -> ClassifyResult {
    if data.is_null() || len == 0 {
        return ClassifyResult {
            is_valid: false, protocol: 0, dest_port: 0, error_code: 1, // 1 = PacketTooShort/Null
        };
    }

    // Unsafe block justification: We cross the FFI boundary here.
    // We assume VPP passes a valid vlib_buffer_t payload pointer and length.
    let slice = unsafe { std::slice::from_raw_parts(data, len) };

    match crate::parse_packet(slice) {
        Ok(packet) => {
            let udp = packet.udp.unwrap(); 
            ClassifyResult {
                is_valid: true,
                protocol: 1, // 1 = udp
                dest_port: udp.destination_port,
                error_code: 0,
            }
        }
        Err(e) => {
            ClassifyResult {
                is_valid: false,
                protocol: 0,
                dest_port: 0,
                error_code: map_error_to_code(&e),
            }
        }
    }
}

/// # Safety
/// The caller must ensure that `data` is a valid pointer to a memory block
/// of at least `len` bytes, and that this memory is not mutated while the
/// returned `PacketHandle` is in use.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn packet_parse(data: *const u8, len: usize) -> *mut PacketHandle<'static> {
    if data.is_null() || len == 0 {
        return ptr::null_mut();
    }

    let slice = unsafe { slice::from_raw_parts(data, len) };

    match parse_packet(slice) {
        Ok(packet) => {
            let handle = Box::new(PacketHandle(packet));

            Box::into_raw(handle)
        }
        Err(_) => ptr::null_mut(),
    }
}

/// # Safety
/// The `ptr` must be a valid pointer returned by `packet_parse`, or NULL.
/// It must not be freed more than once (no double-free).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn packet_free(ptr: *mut PacketHandle<'static>) {
    if !ptr.is_null() {
        let _ = unsafe { Box::from_raw(ptr) };
    }
}
