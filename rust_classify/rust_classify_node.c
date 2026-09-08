#include <vlib/vlib.h>
#include <vnet/vnet.h>
#include <vnet/pg/pg.h>
#include <vppinfra/error.h>
#include "network_parser.h"

typedef enum {
    RUST_CLASSIFY_NEXT_FORWARD,
    RUST_CLASSIFY_NEXT_DROP,
    RUST_CLASSIFY_N_NEXT,
} rust_classify_next_t;

#define foreach_rust_classify_error \
_(FORWARDED_OK, "Valid UDP packets forwarded") \
_(MALFORMED_PACKET, "Malformed or too short packets") \
_(UNSUPPORTED_PROTOCOL, "Unsupported protocol (not UDP)")

typedef enum {
#define _(sym,str) RUST_CLASSIFY_ERROR_##sym,
  foreach_rust_classify_error
#undef _
  RUST_CLASSIFY_N_ERROR,
} rust_classify_error_t;

static char * rust_classify_error_strings[] = {
#define _(sym,string) string,
  foreach_rust_classify_error
#undef _
};

typedef struct {
    u8 is_valid;
    u8 protocol;
    u16 dest_port;
    u32 error_code;
} rust_classify_trace_t;

static u8 * format_rust_classify_trace (u8 * s, va_list * args)
{
    CLIB_UNUSED (vlib_main_t * vm) = va_arg (*args, vlib_main_t *);
    CLIB_UNUSED (vlib_node_t * node) = va_arg (*args, vlib_node_t *);
    rust_classify_trace_t * t = va_arg (*args, rust_classify_trace_t *);

    s = format (s, "RUST_CLASSIFY: valid=%d, protocol=%d, dest_port=%d, error_code=%d",
                t->is_valid, t->protocol, t->dest_port, t->error_code);
    return s;
}

VLIB_NODE_FN (rust_classify_node) (vlib_main_t * vm,
                                   vlib_node_runtime_t * node,
                                   vlib_frame_t * frame)
{
    u32 n_left_from, * from, * to_next;
    rust_classify_next_t next_index;

    u32 pkts_forwarded = 0;
    u32 pkts_malformed = 0;
    u32 pkts_unsupported = 0;

    from = vlib_frame_vector_args (frame);
    n_left_from = frame->n_vectors;
    next_index = node->cached_next_index;

    while (n_left_from > 0)
    {
        u32 n_left_to_next;

        vlib_get_next_frame (vm, node, next_index, to_next, n_left_to_next);

        while (n_left_from > 0 && n_left_to_next > 0)
        {
            u32 bi0;
            vlib_buffer_t * b0;
            u32 next0;

            bi0 = from[0];
            to_next[0] = bi0;
            from += 1;
            to_next += 1;
            n_left_from -= 1;
            n_left_to_next -= 1;

            b0 = vlib_get_buffer (vm, bi0);

            u8 *data_ptr = vlib_buffer_get_current(b0);
            u16 len = b0->current_length;

            ClassifyResult res = packet_classify(data_ptr, len);

            if (res.is_valid && res.protocol == 1) {
                next0 = RUST_CLASSIFY_NEXT_FORWARD;
                pkts_forwarded++;
            } else {
                next0 = RUST_CLASSIFY_NEXT_DROP;
                b0->error = node->errors[res.is_valid ? RUST_CLASSIFY_ERROR_UNSUPPORTED_PROTOCOL : RUST_CLASSIFY_ERROR_MALFORMED_PACKET];
                if (!res.is_valid) pkts_malformed++;
                else pkts_unsupported++;
            }

            // --- TRACE LOGIC ---
            if (PREDICT_FALSE((node->flags & VLIB_NODE_FLAG_TRACE)
                              && (b0->flags & VLIB_BUFFER_IS_TRACED))) {
                rust_classify_trace_t *t = vlib_add_trace (vm, node, b0, sizeof (*t));
                t->is_valid = res.is_valid;
                t->protocol = res.protocol;
                t->dest_port = res.dest_port;
                t->error_code = res.error_code;
            }

            vlib_validate_buffer_enqueue_x1 (vm, node, next_index,
                                             to_next, n_left_to_next,
                                             bi0, next0);
        }

        vlib_put_next_frame (vm, node, next_index, n_left_to_next);
    }

    vlib_node_increment_counter (vm, node->node_index, RUST_CLASSIFY_ERROR_FORWARDED_OK, pkts_forwarded);
    vlib_node_increment_counter (vm, node->node_index, RUST_CLASSIFY_ERROR_MALFORMED_PACKET, pkts_malformed);
    vlib_node_increment_counter (vm, node->node_index, RUST_CLASSIFY_ERROR_UNSUPPORTED_PROTOCOL, pkts_unsupported);

    return frame->n_vectors;
}

VLIB_REGISTER_NODE (rust_classify_node) = {
    .name = "rust-classify-node",
    .vector_size = sizeof (u32),
    .format_trace = format_rust_classify_trace, 
    .type = VLIB_NODE_TYPE_INTERNAL,

    .n_errors = ARRAY_LEN(rust_classify_error_strings),
    .error_strings = rust_classify_error_strings,

    .n_next_nodes = RUST_CLASSIFY_N_NEXT,
    .next_nodes = {
        [RUST_CLASSIFY_NEXT_FORWARD] = "ip4-lookup",
        [RUST_CLASSIFY_NEXT_DROP] = "error-drop",
    },
};