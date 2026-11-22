/* pn_sim: run the device player on mini and record what the panel shows.
 *
 *   pn_sim <pack.pnpk> <frames.rgb> <audio.s16> <events.csv> [options]
 *
 *   --speaker m5|i2s|none  the audio output to imitate (default m5)
 *   --panel-fps N          how often the panel is recorded (default 60)
 *   --loop-us N            time one pass of the firmware loop takes (default 2000)
 *   --draw-us N            time one mouth frame takes to reach the glass
 *                          (default: 3300 for 1-bit over I2C, 700 for RGB565)
 *   --lead-us N            the HAL's draw_lead_us (default: 2 x loop-us + draw-us:
 *                          one pass to notice the audio position, one pass
 *                          until the next step, and the draw)
 *
 * The simulator compiles the same pn_player.c as the firmware and drives it
 * through the same HAL, on a clock that it advances itself:
 *
 *   - The speaker plays at exactly the pack's sample rate. "m5" behaves as
 *     M5Unified's Speaker does: it holds the chunk that plays and one more,
 *     and takes whole chunks only. "i2s" is a FIFO of 512 samples that
 *     takes part of a chunk. "none" has no speaker, so the player falls
 *     back to the clock.
 *   - The panel is a block of display memory in the panel's own format:
 *     8 pages of 128 bytes for the 1-bit panel, 16-bit pixels for RGB565.
 *     draw_base and draw_frame copy pack bytes into it, as the firmware's
 *     display calls do.
 *
 * Output: frames.rgb holds the display memory as RGB24, once per panel
 * frame; audio.s16 holds what the speaker played (int16 mono, silence
 * where it ran dry); events.csv lists every draw with its time.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pn_player.h"

#define I2S_FIFO 512

typedef struct {
    uint64_t now_us;
    /* panel */
    const pn_pack *pack;
    uint8_t *mem;      /* display memory, panel format */
    uint32_t draw_us;
    FILE *events;
    /* speaker */
    int speaker;       /* 0 none, 1 m5, 2 i2s */
    uint32_t rate;
    int16_t *played;   /* everything the speaker has been given, in order */
    uint64_t given;    /* samples accepted */
    uint64_t heard;    /* samples that have left the speaker, with gaps */
    uint64_t queue_end[2]; /* m5: `given` at the end of the playing and the waiting chunk */
    int queued;        /* m5: chunks held, 0 to 2 */
    FILE *audio_out;
    uint64_t audio_us; /* time up to which the speaker output is written */
    uint64_t out_pos;  /* samples of `played` already written */
    uint32_t underruns;
    FILE *frames;
    uint64_t tick, panel_fps, end_us;
} sim;

static void fail(const char *msg)
{
    fprintf(stderr, "pn_sim: %s\n", msg);
    exit(1);
}

/* Advance the speaker to `to_us`: write what it played, silence if dry. */
static void speaker_run(sim *s, uint64_t to_us)
{
    if (!s->audio_out) return;
    /* Output sample k leaves the speaker at k / rate seconds. */
    uint64_t want = to_us * s->rate / 1000000u;
    while (s->heard < want) {
        int16_t v = 0;
        if (s->out_pos < s->given) {
            v = s->played[s->out_pos++];
            if (s->speaker == 1 && s->queued && s->out_pos >= s->queue_end[0]) {
                s->queue_end[0] = s->queue_end[1];
                s->queued--;
            }
        } else if (s->out_pos > 0 && s->out_pos < s->pack->sample_count) {
            s->underruns++;
        }
        fwrite(&v, 2, 1, s->audio_out);
        s->heard++;
    }
    s->audio_us = to_us;
}

static void emit_panel(const sim *s, FILE *out);

/* Move the clock forward. Panel frame k is recorded at k / panel_fps
 * seconds and shows the display memory as it is at that instant, so the
 * frames that fall inside the step are written before the time changes. */
static void advance(sim *s, uint64_t us)
{
    uint64_t to = s->now_us + us;
    for (;;) {
        uint64_t t = s->tick * 1000000u / s->panel_fps;
        if (t >= to || t >= s->end_us) break;
        emit_panel(s, s->frames);
        s->tick++;
    }
    s->now_us = to;
    speaker_run(s, to);
}

static uint64_t hal_micros(void *ctx) { return ((sim *)ctx)->now_us; }

static uint32_t hal_audio_write(void *ctx, const int16_t *samples, uint32_t n, uint32_t rate)
{
    sim *s = (sim *)ctx;
    (void)rate;
    speaker_run(s, s->now_us);
    uint32_t take = n;
    if (s->speaker == 1) {
        if (s->queued >= 2) return 0;
        s->queue_end[s->queued++] = s->given + n;
    } else {
        uint64_t held = s->given - s->out_pos;
        uint32_t room = held >= I2S_FIFO ? 0 : (uint32_t)(I2S_FIFO - held);
        if (take > room) take = room;
    }
    memcpy(s->played + s->given, samples, take * sizeof(int16_t));
    s->given += take;
    return take;
}

static void blit(sim *s, const pn_rect *r, const uint8_t *src)
{
    const pn_pack *k = s->pack;
    if (k->pixel_format == PN_PIX_MONO_VPAGE) {
        for (uint32_t page = 0; page < r->h / 8u; page++)
            memcpy(s->mem + (r->y / 8u + page) * k->panel_w + r->x, src + page * r->w, r->w);
    } else {
        for (uint32_t row = 0; row < r->h; row++)
            memcpy(s->mem + ((uint32_t)(r->y + row) * k->panel_w + r->x) * 2, src + row * r->w * 2u, r->w * 2u);
    }
}

static void hal_draw_base(void *ctx, const pn_pack *pack)
{
    sim *s = (sim *)ctx;
    blit(s, &pack->base, pack->base_image);
    fprintf(s->events, "%llu,base,-1\n", (unsigned long long)s->now_us);
}

static void hal_draw_frame(void *ctx, const pn_pack *pack, int frame)
{
    sim *s = (sim *)ctx;
    /* The frame is on the glass when the transfer ends. */
    advance(s, s->draw_us);
    blit(s, &pack->mouth, pn_pack_frame(pack, frame));
    fprintf(s->events, "%llu,frame,%d\n", (unsigned long long)s->now_us, frame);
}

/* Write the display memory as RGB24, as the panel shows it. */
static void emit_panel(const sim *s, FILE *out)
{
    const pn_pack *k = s->pack;
    static uint8_t row[4096 * 3];
    for (uint32_t y = 0; y < k->panel_h; y++) {
        for (uint32_t x = 0; x < k->panel_w; x++) {
            uint8_t *px = row + x * 3;
            if (k->pixel_format == PN_PIX_MONO_VPAGE) {
                uint8_t on = (s->mem[(y / 8) * k->panel_w + x] >> (y & 7)) & 1;
                px[0] = px[1] = px[2] = on ? 255 : 0;
            } else {
                const uint8_t *p = s->mem + (y * k->panel_w + x) * 2;
                uint16_t v = (uint16_t)((p[0] << 8) | p[1]);
                uint8_t r = v >> 11, g = (v >> 5) & 63, b = v & 31;
                px[0] = (uint8_t)((r << 3) | (r >> 2));
                px[1] = (uint8_t)((g << 2) | (g >> 4));
                px[2] = (uint8_t)((b << 3) | (b >> 2));
            }
        }
        fwrite(row, 3, k->panel_w, out);
    }
}

int main(int argc, char **argv)
{
    if (argc < 5) fail("usage: pn_sim <pack> <frames.rgb> <audio.s16> <events.csv> [options]");
    const char *speaker = "m5";
    long panel_fps = 60, loop_us = 2000, draw_us = -1, lead_us = -1;
    for (int i = 5; i + 1 < argc; i += 2) {
        if (!strcmp(argv[i], "--speaker")) speaker = argv[i + 1];
        else if (!strcmp(argv[i], "--panel-fps")) panel_fps = atol(argv[i + 1]);
        else if (!strcmp(argv[i], "--loop-us")) loop_us = atol(argv[i + 1]);
        else if (!strcmp(argv[i], "--draw-us")) draw_us = atol(argv[i + 1]);
        else if (!strcmp(argv[i], "--lead-us")) lead_us = atol(argv[i + 1]);
        else fail("unknown option");
    }

    FILE *f = fopen(argv[1], "rb");
    if (!f) fail("cannot open the pack");
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *data = malloc((size_t)size);
    if (fread(data, 1, (size_t)size, f) != (size_t)size) fail("cannot read the pack");
    fclose(f);

    pn_pack pack;
    int err = pn_pack_open(&pack, data, (uint32_t)size);
    if (err) fail(pn_error_text(err));
    if (pack.panel_w > 4096) fail("panel too wide");
    if (draw_us < 0) draw_us = pack.pixel_format == PN_PIX_MONO_VPAGE ? 3300 : 700;
    if (lead_us < 0) lead_us = 2 * loop_us + draw_us;

    sim s;
    memset(&s, 0, sizeof s);
    s.pack = &pack;
    s.rate = pack.sample_rate;
    s.draw_us = (uint32_t)draw_us;
    s.mem = calloc(pn_image_bytes(pack.pixel_format, pack.panel_w, (uint16_t)((pack.panel_h + 7) & ~7)), 1);
    s.played = calloc(pack.sample_count + PN_CHUNK, sizeof(int16_t));
    s.speaker = !strcmp(speaker, "m5") ? 1 : !strcmp(speaker, "i2s") ? 2 : 0;
    if (!s.speaker && strcmp(speaker, "none")) fail("--speaker takes m5, i2s, or none");
    s.frames = fopen(argv[2], "wb");
    s.panel_fps = (uint64_t)panel_fps;
    s.end_us = (uint64_t)pack.sample_count * 1000000u / pack.sample_rate;
    s.audio_out = fopen(argv[3], "wb");
    s.events = fopen(argv[4], "w");
    if (!s.frames || !s.audio_out || !s.events) fail("cannot open an output file");
    fprintf(s.events, "time_us,event,frame\n");

    pn_hal hal;
    memset(&hal, 0, sizeof hal);
    hal.ctx = &s;
    hal.micros = hal_micros;
    hal.audio_write = s.speaker ? hal_audio_write : 0;
    hal.draw_base = hal_draw_base;
    hal.draw_frame = hal_draw_frame;
    hal.latency_samples = s.speaker == 1 ? PN_CHUNK : I2S_FIFO;
    hal.draw_lead_us = (uint32_t)lead_us;

    static pn_player player;
    pn_player_begin(&player, &pack, &hal);

    uint64_t steps = 0;
    int playing = 1;
    while (playing || s.now_us < s.end_us) {
        if (playing) playing = pn_player_step(&player);
        advance(&s, (uint64_t)loop_us);
        steps++;
    }
    fclose(s.audio_out);
    fclose(s.frames);
    fclose(s.events);
    fprintf(stderr,
            "pn_sim: %ux%u, %llu panel frames at %ld fps, %llu steps, %u frame changes, speaker %s, "
            "%llu of %u samples given, %u underrun samples\n",
            pack.panel_w, pack.panel_h, (unsigned long long)s.tick, panel_fps, (unsigned long long)steps,
            player.frame_changes, speaker, (unsigned long long)s.given, pack.sample_count, s.underruns);
    return 0;
}
