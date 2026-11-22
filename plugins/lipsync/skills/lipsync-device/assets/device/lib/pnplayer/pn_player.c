/* pn_player: see pn_player.h for the pack layout and the rules. */
#include "pn_player.h"

#include <string.h>

static uint16_t rd16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t rd24(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16); }
static uint32_t rd32(const uint8_t *p) { return rd24(p) | ((uint32_t)p[3] << 24); }

static void rd_rect(pn_rect *r, const uint8_t *p)
{
    r->x = rd16(p);
    r->y = rd16(p + 2);
    r->w = rd16(p + 4);
    r->h = rd16(p + 6);
}

uint32_t pn_image_bytes(uint8_t pixel_format, uint16_t w, uint16_t h)
{
    if (pixel_format == PN_PIX_MONO_VPAGE) return (uint32_t)w * (h / 8);
    if (pixel_format == PN_PIX_RGB565_BE) return (uint32_t)w * h * 2;
    return 0;
}

static int rect_ok(const pn_pack *k, const pn_rect *r)
{
    if (r->w == 0 || r->h == 0) return 0;
    if ((uint32_t)r->x + r->w > k->panel_w || (uint32_t)r->y + r->h > k->panel_h) return 0;
    if (k->pixel_format == PN_PIX_MONO_VPAGE && ((r->x | r->y | r->w | r->h) & 7)) return 0;
    return 1;
}

/* True when [off, off + len) lies inside the pack. */
static int span_ok(const pn_pack *k, uint32_t off, uint32_t len)
{
    return off >= PN_HEADER_SIZE && off <= k->size && len <= k->size - off;
}

static int pack_parse(pn_pack *k, const uint8_t *d, uint32_t size)
{
    memset(k, 0, sizeof *k);
    if (size < PN_HEADER_SIZE) return PN_ERR_SIZE;
    if (memcmp(d, "PNPK", 4) != 0) return PN_ERR_MAGIC;
    if (d[4] != PN_VERSION) return PN_ERR_VERSION;
    k->data = d;
    k->size = size;
    k->pixel_format = d[5];
    k->audio_format = d[6];
    k->frame_count = d[7];
    k->panel_w = rd16(d + 8);
    k->panel_h = rd16(d + 10);
    rd_rect(&k->base, d + 12);
    rd_rect(&k->mouth, d + 20);
    k->sample_rate = rd32(d + 28);
    k->sample_count = rd32(d + 32);
    k->run_count = rd32(d + 36);
    k->adpcm_block = rd16(d + 40);
    k->closed_mask = rd16(d + 42);
    k->audio_bytes = rd32(d + 60);

    if (k->pixel_format != PN_PIX_MONO_VPAGE && k->pixel_format != PN_PIX_RGB565_BE) return PN_ERR_FORMAT;
    if (k->audio_format > PN_AUDIO_IMA_ADPCM) return PN_ERR_FORMAT;
    if (k->frame_count == 0 || k->frame_count > PN_MAX_FRAMES) return PN_ERR_FORMAT;
    if (!rect_ok(k, &k->base) || !rect_ok(k, &k->mouth)) return PN_ERR_FORMAT;
    if (k->sample_rate == 0 || k->sample_count == 0 || k->run_count == 0) return PN_ERR_FORMAT;
    k->frame_bytes = pn_image_bytes(k->pixel_format, k->mouth.w, k->mouth.h);

    uint32_t base_off = rd32(d + 44), frames_off = rd32(d + 48), runs_off = rd32(d + 52), audio_off = rd32(d + 56);
    if (k->run_count > 0x3FFFFFFFu) return PN_ERR_SIZE;
    if (!span_ok(k, base_off, pn_image_bytes(k->pixel_format, k->base.w, k->base.h))) return PN_ERR_SIZE;
    if (!span_ok(k, frames_off, k->frame_bytes * k->frame_count)) return PN_ERR_SIZE;
    if (!span_ok(k, runs_off, k->run_count * 4)) return PN_ERR_SIZE;
    if (!span_ok(k, audio_off, k->audio_bytes)) return PN_ERR_SIZE;
    k->base_image = d + base_off;
    k->frames = d + frames_off;
    k->runs = d + runs_off;
    k->audio = d + audio_off;

    if (k->audio_format == PN_AUDIO_PCM16) {
        if (k->audio_bytes / 2 < k->sample_count) return PN_ERR_SIZE;
    } else if (k->audio_format == PN_AUDIO_IMA_ADPCM) {
        if (k->adpcm_block < 8) return PN_ERR_FORMAT;
        uint32_t per_block = 1 + (uint32_t)(k->adpcm_block - 4) * 2;
        uint32_t blocks = (k->sample_count + per_block - 1) / per_block;
        if (k->audio_bytes / k->adpcm_block < blocks) return PN_ERR_SIZE;
    }

    uint64_t total = 0;
    for (uint32_t i = 0; i < k->run_count; i++) {
        const uint8_t *r = k->runs + i * 4;
        if (r[0] >= k->frame_count) return PN_ERR_PLAN;
        total += rd24(r + 1);
    }
    if (total != k->sample_count) return PN_ERR_PLAN;
    return PN_OK;
}

int pn_pack_open(pn_pack *k, const uint8_t *d, uint32_t size)
{
    int err = pack_parse(k, d, size);
    if (err != PN_OK) memset(k, 0, sizeof *k); /* A failed pack has data == NULL. */
    return err;
}

const uint8_t *pn_pack_frame(const pn_pack *k, int frame)
{
    if (frame < 0 || frame >= k->frame_count) return 0;
    return k->frames + (uint32_t)frame * k->frame_bytes;
}

const char *pn_error_text(int err)
{
    switch (err) {
    case PN_OK: return "ok";
    case PN_ERR_SIZE: return "the pack is cut short";
    case PN_ERR_MAGIC: return "not a PNPK pack";
    case PN_ERR_VERSION: return "unknown pack version";
    case PN_ERR_FORMAT: return "bad format or rectangle";
    case PN_ERR_PLAN: return "bad frame plan";
    default: return "unknown error";
    }
}

/* ------------------------------------------------------------- plan */

static void plan_load(pn_plan *p, uint32_t run, uint32_t start)
{
    p->run = run;
    p->run_start = start;
    p->run_end = start + rd24(p->pack->runs + run * 4 + 1);
}

void pn_plan_init(pn_plan *p, const pn_pack *pack)
{
    p->pack = pack;
    plan_load(p, 0, 0);
}

int pn_plan_frame_at(pn_plan *p, uint32_t sample)
{
    if (sample < p->run_start) plan_load(p, 0, 0);
    while (sample >= p->run_end && p->run + 1 < p->pack->run_count) plan_load(p, p->run + 1, p->run_end);
    return p->pack->runs[p->run * 4];
}

/* ------------------------------------------------------------ audio */

static const int16_t IMA_STEP[89] = {
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107,
    118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,
    1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894,
    6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794,
    32767};
static const int8_t IMA_INDEX[8] = {-1, -1, -1, -1, 2, 4, 6, 8};

void pn_audio_init(pn_audio *a, const pn_pack *pack)
{
    a->pack = pack;
    a->pos = 0;
    a->predictor = 0;
    a->index = 0;
}

static int16_t adpcm_next(pn_audio *a, uint32_t pos)
{
    const pn_pack *k = a->pack;
    uint32_t per_block = 1 + (uint32_t)(k->adpcm_block - 4) * 2;
    const uint8_t *block = k->audio + (pos / per_block) * k->adpcm_block;
    uint32_t in_block = pos % per_block;
    if (in_block == 0) {
        a->predictor = (int16_t)rd16(block);
        a->index = (int8_t)(block[2] > 88 ? 88 : block[2]);
        return a->predictor;
    }
    uint32_t n = in_block - 1;
    uint8_t code = (block[4 + n / 2] >> ((n & 1) * 4)) & 15;
    int step = IMA_STEP[a->index];
    int diff = step >> 3;
    if (code & 4) diff += step;
    if (code & 2) diff += step >> 1;
    if (code & 1) diff += step >> 2;
    int v = a->predictor + ((code & 8) ? -diff : diff);
    if (v > 32767) v = 32767;
    if (v < -32768) v = -32768;
    a->predictor = (int16_t)v;
    int idx = a->index + IMA_INDEX[code & 7];
    if (idx < 0) idx = 0;
    if (idx > 88) idx = 88;
    a->index = (int8_t)idx;
    return a->predictor;
}

uint32_t pn_audio_read(pn_audio *a, int16_t *out, uint32_t n)
{
    const pn_pack *k = a->pack;
    uint32_t left = k->sample_count - a->pos;
    if (k->audio_format == PN_AUDIO_NONE) left = 0;
    if (n > left) n = left;
    if (k->audio_format == PN_AUDIO_PCM16) {
        const uint8_t *src = k->audio + (uint32_t)a->pos * 2;
        for (uint32_t i = 0; i < n; i++) out[i] = (int16_t)rd16(src + i * 2);
        a->pos += n;
    } else {
        for (uint32_t i = 0; i < n; i++) out[i] = adpcm_next(a, a->pos++);
    }
    return n;
}

void pn_audio_seek(pn_audio *a, uint32_t sample)
{
    const pn_pack *k = a->pack;
    if (sample > k->sample_count) sample = k->sample_count;
    if (k->audio_format == PN_AUDIO_IMA_ADPCM) {
        /* Decode from the start of the block to rebuild the decoder state. */
        uint32_t per_block = 1 + (uint32_t)(k->adpcm_block - 4) * 2;
        for (uint32_t p = sample - sample % per_block; p < sample; p++) adpcm_next(a, p);
    }
    a->pos = sample;
}

/* ------------------------------------------------------------ clock */

void pn_clock_init(pn_clock *c, uint32_t rate, uint32_t latency)
{
    memset(c, 0, sizeof *c);
    c->rate = rate;
    c->latency = latency;
}

void pn_clock_start_free(pn_clock *c, uint64_t now_us)
{
    c->free_running = 1;
    c->started = 1;
    c->anchor_us = now_us;
    c->anchor_pos = 0;
}

static uint64_t clock_estimate(const pn_clock *c, uint64_t now_us)
{
    if (!c->started) return 0;
    uint64_t pos = c->anchor_pos;
    if (now_us > c->anchor_us) pos += (now_us - c->anchor_us) * c->rate / 1000000u;
    /* The speaker cannot have played more than it was given. */
    if (!c->free_running && pos > c->submitted) pos = c->submitted;
    return pos;
}

void pn_clock_on_submit(pn_clock *c, uint64_t now_us, uint32_t n, int waited)
{
    uint64_t played = c->submitted > c->latency ? c->submitted - c->latency : 0;
    uint64_t estimate = clock_estimate(c, now_us);
    /* After a wait the output was full, so `played` is exact. Otherwise the
     * output had room (the start, or an underrun) and `played` is only a
     * lower bound: keep the timer's estimate when it is ahead. */
    c->anchor_pos = (waited || played > estimate) ? played : estimate;
    c->anchor_us = now_us;
    c->submitted += n;
    c->started = 1;
}

uint32_t pn_clock_position(pn_clock *c, uint64_t now_us)
{
    uint64_t pos = clock_estimate(c, now_us);
    if (pos < c->last_pos) pos = c->last_pos;
    c->last_pos = pos;
    return pos > 0xFFFFFFFFu ? 0xFFFFFFFFu : (uint32_t)pos;
}

/* ----------------------------------------------------------- player */

void pn_player_begin(pn_player *p, const pn_pack *pack, const pn_hal *hal)
{
    memset(p, 0, sizeof *p);
    p->pack = pack;
    p->hal = hal;
    p->shown = -1;
    p->use_audio = hal->audio_write != 0 && pack->audio_format != PN_AUDIO_NONE;
    pn_plan_init(&p->plan, pack);
    pn_audio_init(&p->audio, pack);
    pn_clock_init(&p->clock, pack->sample_rate, hal->latency_samples);
}

int pn_player_step(pn_player *p)
{
    const pn_hal *hal = p->hal;
    uint64_t now = hal->micros(hal->ctx);
    if (!p->started) {
        p->started = 1;
        hal->draw_base(hal->ctx, p->pack);
        if (!p->use_audio) pn_clock_start_free(&p->clock, hal->micros(hal->ctx));
        now = hal->micros(hal->ctx);
    }
    if (p->use_audio && !p->audio_done) {
        if (p->pending == 0) {
            p->pending = pn_audio_read(&p->audio, p->chunk, PN_CHUNK);
            p->pending_off = 0;
            if (p->pending == 0) p->audio_done = 1;
        }
        if (p->pending) {
            uint32_t took = hal->audio_write(hal->ctx, p->chunk + p->pending_off, p->pending, p->pack->sample_rate);
            if (took > p->pending) took = p->pending;
            if (took) {
                pn_clock_on_submit(&p->clock, now, took, p->waited);
                p->pending_off += took;
                p->pending -= took;
            }
            /* A refusal or a part-accept means the output is full now. */
            p->waited = (uint8_t)(took == 0 || p->pending != 0);
        }
    }
    uint32_t lead = (uint32_t)((uint64_t)hal->draw_lead_us * p->pack->sample_rate / 1000000u);
    uint32_t pos = pn_clock_position(&p->clock, now);
    int frame = pn_plan_frame_at(&p->plan, pos + lead);
    if (frame != p->shown) {
        hal->draw_frame(hal->ctx, p->pack, frame);
        p->shown = frame;
        p->frame_changes++;
    }
    return pos < p->pack->sample_count;
}

uint32_t pn_player_position(const pn_player *p)
{
    return (uint32_t)p->clock.last_pos;
}
