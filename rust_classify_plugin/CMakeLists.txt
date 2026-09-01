add_vpp_plugin(rust_classify
  SOURCES
  rust_classify.c

  # Link the static Rust library. 
  LINK_LIBRARIES
  ${CMAKE_CURRENT_SOURCE_DIR}/../network_parser/target/debug/libnetwork_parser.a
)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../network_parser)