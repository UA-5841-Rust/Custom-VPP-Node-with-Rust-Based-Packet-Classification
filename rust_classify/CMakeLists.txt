add_vpp_plugin(rust_classify
  SOURCES
  rust_classify.c
  rust_classify_node.c
)

set(RUST_LIB_DIR "/mnt/d/Rust projects/Custom-VPP-Node-with-Rust-Based-Packet-Classification/network_parser/target/release")

target_link_libraries(rust_classify_plugin ${RUST_LIB_DIR}/libnetwork_parser.a)