/* pn_player: plays a pixel-narrator device pack on a small screen.
 *
 * A pack (.pnpk) holds one spoken line: the audio, a base image for the
 * panel, the mouth frames, and the frame plan. Mini makes the pack; the
 * device only plays it. The player picks the mouth frame from the audio
 * position, counted in samples that the speaker has played, so the mouth
 * cannot drift from the sound. A board without a speaker uses the clock.
 *
 * The code is C99, needs no operating system, and never calls malloc. All
 * state lives in the caller's pn_player struct. The same file runs in the
 * firmware, in the host simulator (device/sim), and in the unit tests.
 *
 * Pack layout, version 1. All integers are little-endian.
 *
 *   offset size  field
 *   0      4     magic "PNPK"
 *   4      1     version (1)
 *   5      1     pixel format: 1 = PN_PIX_MONO_VPAGE, 2 = PN_PIX_RGB565_BE
 *   6      1     audio format: 0 = none, 1 = PCM16, 2 = IMA ADPCM
 *   7      1     frame count (1 to 16)
 *   8      2+2   panel width, height in pixels
 *   12     2x4   base image rectangle: x, y, width, height
 *   20     2x4   mouth rectangle: x, y, width, height
 *   28     4     audio sample rate in Hz
 *   32     4     audio sample count (the length of the line)
 *   36     4     run count
 *   40     2     ADPCM block size in bytes (0 for other formats)
 *   42     2     closed mask: bit i is set when frame i is a closed mouth
 *   44     4     offset of the base image
 *   48     4     offset of the frames (frame i follows frame i-1)
 *   52     4     offset of the runs
 *   56     4     offset of the audio
 *   60     4     audio size in bytes
 *
 * Pixel formats, both the panel's own:
 *   PN_PIX_MONO_VPAGE  1 bit per pixel in 8-row pages, as SSD1306 and SH1106
 *                      store it: one byte holds 8 pixels of one column, top
 *                      pixel in bit 0; bytes run left to right, then page
 *                      by page. Rectangles start and end on multiples of 8.
 *   PN_PIX_RGB565_BE   16 bits per pixel, high byte first (the byte order
 *                      an ST7789 takes on its SPI bus), row by row.
 *
 * A run is 4 bytes: the frame index (1 byte) and how long it stays, in
 * audio samples (3 bytes). The runs cover the whole line in order.
 *
 * IMA ADPCM audio is stored in blocks that decode on their own: a 4-byte
 * header (first sample as int16, step index, 0), then 4-bit codes, low
 * nibble first. A block of B bytes holds 1 + (B - 4) * 2 samples.
 */
#ifndef PN_PLAYER_H
#define PN_PLAYER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PN_VERSION 1
#define PN_HEADER_SIZE 64
#define PN_MAX_FRAMES 16

/* Samples that the player hands to the speaker at a time: 16 ms at 16 kHz. */
#ifndef PN_CHUNK
#define PN_CHUNK 256
#endif

enum { PN_PIX_MONO_VPAGE = 1, PN_PIX_RGB565_BE = 2 };
enum { PN_AUDIO_NONE = 0, PN_AUDIO_PCM16 = 1, PN_AUDIO_IMA_ADPCM = 2 };

enum {
    PN_OK = 0,
    PN_ERR_SIZE = -1,     /* the buffer is shorter than the pack says */
    PN_ERR_MAGIC = -2,
    PN_ERR_VERSION = -3,
    PN_ERR_FORMAT = -4,   /* unknown pixel or audio format, or a bad rectangle */
    PN_ERR_PLAN = -5      /* a run names a missing frame, or the runs do not add up */
};

typedef struct {
    uint16_t x, y, w, h;
} pn_rect;

typedef struct {
    const uint8_t *data;
    uint32_t size;
    uint8_t pixel_format, audio_format, frame_count;
    uint16_t panel_w, panel_h;
    pn_rect base, mouth;
    uint32_t sample_rate, sample_count, run_count;
    uint16_t adpcm_block, closed_mask;
    uint32_t frame_bytes; /* size of one mouth frame */
    const uint8_t *base_image, *frames, *runs, *audio;
    uint32_t audio_bytes;
} pn_pack;

/* Parse and check a pack that stays in memory (flash) while it plays. */
int pn_pack_open(pn_pack *pack, const uint8_t *data, uint32_t size);
const uint8_t *pn_pack_frame(const pn_pack *pack, int frame);
/* Bytes of an image of w x h pixels in the given pixel format. */
uint32_t pn_image_bytes(uint8_t pixel_format, uint16_t w, uint16_t h);
const char *pn_error_text(int err);

/* ---- The frame plan: which frame is on screen at an audio position. ---- */

typedef struct {
    const pn_pack *pack;
    uint32_t run;        /* index of the current run */
    uint32_t run_start;  /* first sample of the current run */
    uint32_t run_end;    /* first sample after it */
} pn_plan;

void pn_plan_init(pn_plan *plan, const pn_pack *pack);
/* Frame index at `sample`. Cheap when positions rise; a lower position
 * than the last one restarts the search from the first run. */
int pn_plan_frame_at(pn_plan *plan, uint32_t sample);

/* ---- The audio stream: decode the pack's audio in small pieces. ---- */

typedef struct {
    const pn_pack *pack;
    uint32_t pos;        /* next sample to decode */
    int16_t predictor;   /* ADPCM state */
    int8_t index;
} pn_audio;

void pn_audio_init(pn_audio *audio, const pn_pack *pack);
/* Decode up to n samples into out. Returns the count; 0 at the end. */
uint32_t pn_audio_read(pn_audio *audio, int16_t *out, uint32_t n);
/* Move to a sample position (clamped to the length of the line). */
void pn_audio_seek(pn_audio *audio, uint32_t sample);

/* ---- The clock: how many samples the speaker has played. ---- */

typedef struct {
    uint32_t rate;
    uint32_t latency;      /* samples the audio output holds when it is full */
    uint64_t submitted;    /* samples handed to the output so far */
    uint64_t anchor_pos;   /* samples played at anchor_us */
    uint64_t anchor_us;
    uint64_t last_pos;     /* the position never goes back */
    uint8_t started, free_running;
} pn_clock;

void pn_clock_init(pn_clock *clock, uint32_t rate, uint32_t latency);
/* Start a clock with no speaker: the position follows the timer alone. */
void pn_clock_start_free(pn_clock *clock, uint64_t now_us);
/* Call when the output accepted n samples. `waited` is nonzero when the
 * output was full just before: then exactly `latency` samples were still
 * unplayed, which fixes the position. */
void pn_clock_on_submit(pn_clock *clock, uint64_t now_us, uint32_t n, int waited);
uint32_t pn_clock_position(pn_clock *clock, uint64_t now_us);

/* ---- The player: ties the three to a board through a small HAL. ---- */

typedef struct pn_hal {
    void *ctx;
    /* Microseconds from any fixed start; must not wrap during a line. */
    uint64_t (*micros)(void *ctx);
    /* Hand samples to the speaker without blocking. Returns how many it
     * took, 0 when it is full. NULL on a board with no speaker. */
    uint32_t (*audio_write)(void *ctx, const int16_t *samples, uint32_t n, uint32_t rate);
    /* Draw the base image, then one mouth frame at the mouth rectangle. */
    void (*draw_base)(void *ctx, const pn_pack *pack);
    void (*draw_frame)(void *ctx, const pn_pack *pack, int frame);
    /* Samples the audio output holds when full (see pn_clock). */
    uint32_t latency_samples;
    /* Time one frame takes to reach the glass, in microseconds. The player
     * asks for the frame that is due this much later. */
    uint32_t draw_lead_us;
} pn_hal;

typedef struct {
    const pn_pack *pack;
    const pn_hal *hal;
    pn_plan plan;
    pn_audio audio;
    pn_clock clock;
    int16_t chunk[PN_CHUNK];
    uint32_t pending, pending_off;  /* samples of chunk not yet accepted */
    int shown;                      /* frame on the panel, -1 before the first */
    uint32_t frame_changes;
    uint8_t started, waited, audio_done, use_audio;
} pn_player;

void pn_player_begin(pn_player *player, const pn_pack *pack, const pn_hal *hal);
/* Call often (every few milliseconds). Returns 1 while the line plays and
 * 0 when it has finished. Never blocks and never allocates. */
int pn_player_step(pn_player *player);
/* The audio position of the last step, in samples. */
uint32_t pn_player_position(const pn_player *player);

#ifdef __cplusplus
}
#endif

#endif
