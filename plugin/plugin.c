#include <vlib/vlib.h>
#include <vnet/vnet.h>
#include <vnet/feature/feature.h>
#include <vnet/plugin/plugin.h>
#include <vpp/app/version.h>

VLIB_PLUGIN_REGISTER () = {
  .version = VPP_BUILD_VER,
  .description = "Zero-copy Rust Ethernet/IPv4/UDP classifier",
};

VNET_FEATURE_INIT (rust_classify_feature, static) = {
  .arc_name = "device-input",
  .node_name = "rust-classify-node",
  .runs_before = VNET_FEATURES ("ethernet-input"),
};

static clib_error_t *
rust_classify_command_fn (vlib_main_t *vm, unformat_input_t *input,
                         vlib_cli_command_t *cmd)
{
  vnet_main_t *vnm = vnet_get_main ();
  u32 sw_if_index = ~0;
  int enable = 1;
  int rv;
  while (unformat_check_input (input) != UNFORMAT_END_OF_INPUT)
    {
      if (unformat (input, "disable"))
        enable = 0;
      else if (unformat (input, "%U", unformat_vnet_sw_interface, vnm,
                         &sw_if_index))
        ;
      else
        return clib_error_return (0, "unknown input: %U", format_unformat_error,
                                  input);
    }
  if (sw_if_index == ~0)
    return clib_error_return (0, "specify an Ethernet hardware interface");
  vnet_sw_interface_t *sw = vnet_get_sw_interface (vnm, sw_if_index);
  if (sw->type != VNET_SW_INTERFACE_TYPE_HARDWARE)
    return clib_error_return (0, "subinterfaces are not supported");
  rv = vnet_feature_enable_disable ("device-input", "rust-classify-node",
                                    sw_if_index, enable, 0, 0);
  if (rv)
    return clib_error_return (0, "feature enable/disable failed: %d", rv);
  return 0;
}

/* CLI execution uses the default worker barrier (not mp_safe). No mutable
 * plugin-global data is accessed from packet-processing workers. */
VLIB_CLI_COMMAND (rust_classify_command, static) = {
  .path = "rust classify",
  .short_help = "rust classify <interface> [disable]",
  .function = rust_classify_command_fn,
};
