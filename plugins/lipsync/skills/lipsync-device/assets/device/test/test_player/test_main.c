/* Unit tests of pn_player on the build machine: pio test -e native
 *
 * The fixture packs come from the Python exporter (tools/make_fixture.py),
 * so these tests also hold the exporter and the player to one byte layout.
 */
#include <stdlib.h>
#include <string.h>
#include <unity.h>

#include "fixture.h"
#include "pn_player.h"

void setUp(void) {}
void tearDown(void) {}

static pn_pack open_mono(void)
{
    pn_pack k;
    TEST_ASSERT_EQUAL_INT(PN_OK, pn_pack_open(&k, FIXTURE_MONO, sizeof FIXTURE_MONO));
    return k;
}

/* ------------------------------------------------------------- pack */

static void test_open_reads_the_header(void)
{
    pn_pack k = open_mono();
    TEST_ASSERT_EQUAL_UINT8(PN_PIX_MONO_VPAGE, k.pixel_format);
    TEST_ASSERT_EQUAL_UINT8(PN_AUDIO_IMA_ADPCM, k.audio_format);
    TEST_ASSERT_EQUAL_UINT8(3, k.frame_count);
    TEST_ASSERT_EQUAL_UINT16(16, k.panel_w);
    TEST_ASSERT_EQUAL_UINT16(16, k.panel_h);
    TEST_ASSERT_EQUAL_UINT16(8, k.mouth.x);
    TEST_ASSERT_EQUAL_UINT16(8, k.mouth.y);
    TEST_ASSERT_EQUAL_UINT16(8, k.mouth.w);
    TEST_ASSERT_EQUAL_UINT16(8, k.mouth.h);
    TEST_ASSERT_EQUAL_UINT32(8000, k.sample_rate);
    TEST_ASSERT_EQUAL_UINT32(1200, k.sample_count);
    TEST_ASSERT_EQUAL_UINT32(5, k.run_count);
    TEST_ASSERT_EQUAL_UINT16(1, k.closed_mask);
    TEST_ASSERT_EQUAL_UINT32(8, k.frame_bytes);
    TEST_ASSERT_EQUAL_UINT8(1, k.base_image[0]);
    TEST_ASSERT_EQUAL_UINT8(32, k.base_image[31]);
    TEST_ASSERT_EQUAL_UINT8(0x20, pn_pack_frame(&k, 1)[0]);
    TEST_ASSERT_EQUAL_UINT8(0x37, pn_pack_frame(&k, 2)[7]);
    TEST_ASSERT_NULL(pn_pack_frame(&k, 3));
    TEST_ASSERT_NULL(pn_pack_frame(&k, -1));
}

static void test_open_reads_a_colour_pack(void)
{
    pn_pack k;
    TEST_ASSERT_EQUAL_INT(PN_OK, pn_pack_open(&k, FIXTURE_COLOR, sizeof FIXTURE_COLOR));
    TEST_ASSERT_EQUAL_UINT8(PN_PIX_RGB565_BE, k.pixel_format);
    TEST_ASSERT_EQUAL_UINT32(12, k.frame_bytes);
    TEST_ASSERT_EQUAL_UINT16(2, k.closed_mask);
    TEST_ASSERT_EQUAL_UINT8(100, k.base_image[0]);
    TEST_ASSERT_EQUAL_UINT8(30, pn_pack_frame(&k, 1)[0]);
    pn_audio a;
    int16_t out[64];
    pn_audio_init(&a, &k);
    TEST_ASSERT_EQUAL_UINT32(40, pn_audio_read(&a, out, 64));
    TEST_ASSERT_EQUAL_INT16_ARRAY(FIXTURE_COLOR_PCM, out, 40);
    TEST_ASSERT_EQUAL_UINT32(0, pn_audio_read(&a, out, 64));
}

/* Open a copy of the mono fixture with one byte changed. */
static int open_changed(uint32_t offset, uint8_t value, uint32_t size)
{
    static uint8_t copy[sizeof FIXTURE_MONO];
    pn_pack k;
    memcpy(copy, FIXTURE_MONO, sizeof copy);
    copy[offset] = value;
    int err = pn_pack_open(&k, copy, size);
    if (err != PN_OK) TEST_ASSERT_NULL(k.data);
    return err;
}

static void test_open_rejects_bad_packs(void)
{
    uint32_t full = sizeof FIXTURE_MONO;
    TEST_ASSERT_EQUAL_INT(PN_OK, open_changed(0, 'P', full));
    TEST_ASSERT_EQUAL_INT(PN_ERR_SIZE, open_changed(0, 'P', 63));
    TEST_ASSERT_EQUAL_INT(PN_ERR_SIZE, open_changed(0, 'P', full - 1));   /* audio cut short */
    TEST_ASSERT_EQUAL_INT(PN_ERR_MAGIC, open_changed(0, 'X', full));
    TEST_ASSERT_EQUAL_INT(PN_ERR_VERSION, open_changed(4, 2, full));
    TEST_ASSERT_EQUAL_INT(PN_ERR_FORMAT, open_changed(5, 9, full));       /* pixel format */
    TEST_ASSERT_EQUAL_INT(PN_ERR_FORMAT, open_changed(6, 3, full));       /* audio format */
    TEST_ASSERT_EQUAL_INT(PN_ERR_FORMAT, open_changed(7, 0, full));       /* no frames */
    TEST_ASSERT_EQUAL_INT(PN_ERR_FORMAT, open_changed(7, 17, full));
    TEST_ASSERT_EQUAL_INT(PN_ERR_FORMAT, open_changed(20, 12, full));     /* mouth x off the tile grid */
    TEST_ASSERT_EQUAL_INT(PN_ERR_FORMAT, open_changed(22, 16, full));     /* mouth below the panel */
    TEST_ASSERT_EQUAL_INT(PN_ERR_SIZE, open_changed(47, 0x7F, full));     /* base offset far outside */
    TEST_ASSERT_EQUAL_INT(PN_ERR_PLAN, open_changed(32, 0xB1, full));     /* sample count != sum of runs */
    pn_pack k = open_mono();
    uint32_t runs_off = (uint32_t)(k.runs - k.data);
    TEST_ASSERT_EQUAL_INT(PN_ERR_PLAN, open_changed(runs_off, 3, full));  /* a run names frame 3 of 3 */
}

/* ------------------------------------------------------------- plan */

static void test_plan_follows_the_runs(void)
{
    pn_pack k = open_mono();
    pn_plan p;
    pn_plan_init(&p, &k);
    /* Runs: frame 0 x200, 1 x333, 2 x67, 1 x400, 0 x200. */
    TEST_ASSERT_EQUAL_INT(0, pn_plan_frame_at(&p, 0));
    TEST_ASSERT_EQUAL_INT(0, pn_plan_frame_at(&p, 199));
    TEST_ASSERT_EQUAL_INT(1, pn_plan_frame_at(&p, 200));
    TEST_ASSERT_EQUAL_INT(1, pn_plan_frame_at(&p, 532));
    TEST_ASSERT_EQUAL_INT(2, pn_plan_frame_at(&p, 533));
    TEST_ASSERT_EQUAL_INT(2, pn_plan_frame_at(&p, 599));
    TEST_ASSERT_EQUAL_INT(1, pn_plan_frame_at(&p, 600));
    TEST_ASSERT_EQUAL_INT(0, pn_plan_frame_at(&p, 1000));
    TEST_ASSERT_EQUAL_INT(0, pn_plan_frame_at(&p, 1199));
    TEST_ASSERT_EQUAL_INT(0, pn_plan_frame_at(&p, 1200));       /* at the end */
    TEST_ASSERT_EQUAL_INT(0, pn_plan_frame_at(&p, 4000000));    /* far past it */
    TEST_ASSERT_EQUAL_INT(2, pn_plan_frame_at(&p, 540));        /* back: the search restarts */
    TEST_ASSERT_EQUAL_INT(0, pn_plan_frame_at(&p, 3));
    TEST_ASSERT_EQUAL_INT(1, pn_plan_frame_at(&p, 999));        /* a jump over two runs */
}

/* ------------------------------------------------------------ audio */

static void test_adpcm_matches_the_exporter(void)
{
    pn_pack k = open_mono();
    pn_audio a;
    static int16_t out[1300];
    /* Uneven pieces, so block edges fall inside a read. */
    static const uint32_t sizes[] = {1, 7, 256, 3, 500, 64, 1000};
    uint32_t got = 0, i = 0;
    pn_audio_init(&a, &k);
    for (;;) {
        uint32_t n = pn_audio_read(&a, out + got, sizes[i++ % 7]);
        if (n == 0) break;
        got += n;
    }
    TEST_ASSERT_EQUAL_UINT32(1200, got);
    TEST_ASSERT_EQUAL_INT16_ARRAY(FIXTURE_PCM, out, 1200);
}

static void test_audio_seek(void)
{
    pn_pack k = open_mono();
    pn_audio a;
    int16_t out[100];
    static const uint32_t starts[] = {0, 1, 504, 505, 506, 777, 1010, 1150};
    pn_audio_init(&a, &k);
    for (unsigned s = 0; s < sizeof starts / sizeof starts[0]; s++) {
        pn_audio_seek(&a, starts[s]);
        uint32_t want = 1200 - starts[s] < 50 ? 1200 - starts[s] : 50;
        TEST_ASSERT_EQUAL_UINT32(want, pn_audio_read(&a, out, 50));
        TEST_ASSERT_EQUAL_INT16_ARRAY(FIXTURE_PCM + starts[s], out, want);
    }
    pn_audio_seek(&a, 99999);
    TEST_ASSERT_EQUAL_UINT32(0, pn_audio_read(&a, out, 50));
}

/* ------------------------------------------------------------ clock */

static void test_clock_without_a_speaker_follows_the_timer(void)
{
    pn_clock c;
    pn_clock_init(&c, 16000, 0);
    TEST_ASSERT_EQUAL_UINT32(0, pn_clock_position(&c, 5000000));  /* not started */
    pn_clock_start_free(&c, 1000000);
    TEST_ASSERT_EQUAL_UINT32(0, pn_clock_position(&c, 1000000));
    TEST_ASSERT_EQUAL_UINT32(16000, pn_clock_position(&c, 2000000));
    TEST_ASSERT_EQUAL_UINT32(16000, pn_clock_position(&c, 1500000));  /* never goes back */
    TEST_ASSERT_EQUAL_UINT32(16 * 3600, pn_clock_position(&c, 1000000 + 3600000));
}

static void test_clock_never_passes_what_was_submitted(void)
{
    pn_clock c;
    pn_clock_init(&c, 16000, 256);
    pn_clock_on_submit(&c, 0, 256, 0);
    TEST_ASSERT_EQUAL_UINT32(160, pn_clock_position(&c, 10000));
    TEST_ASSERT_EQUAL_UINT32(256, pn_clock_position(&c, 10000000));  /* a stalled feed stalls the mouth */
}

static void test_clock_anchors_to_the_samples_played(void)
{
    /* The device timer runs 2% fast against the audio clock. A free timer
     * would be 0.2 s ahead after 10 s. The anchored clock is never more
     * than 2% of one chunk (6 samples) from the truth, because every
     * accepted chunk resets it. */
    const uint32_t rate = 16000, chunk = 256;
    pn_clock c;
    pn_clock_init(&c, rate, chunk);
    uint64_t submitted = 0;
    uint32_t worst = 0;
    pn_clock_on_submit(&c, 0, chunk, 0);
    pn_clock_on_submit(&c, 0, chunk, 0);
    submitted = 2 * chunk;
    for (uint32_t k = 1; k < 625; k++) {
        /* True time at which chunk k starts and a slot frees. */
        uint64_t true_us = (uint64_t)k * chunk * 1000000u / rate;
        uint64_t timer_us = true_us * 102 / 100;
        /* Just before the submit, compare the estimate with the truth. */
        uint32_t est = pn_clock_position(&c, timer_us);
        uint32_t truth = k * chunk;
        uint32_t diff = est > truth ? est - truth : truth - est;
        if (diff > worst) worst = diff;
        TEST_ASSERT_TRUE(est <= submitted);
        pn_clock_on_submit(&c, timer_us, chunk, 1);
        submitted += chunk;
        /* The position never steps back, so it may keep the few samples it ran ahead. */
        TEST_ASSERT_UINT32_WITHIN(6, truth, pn_clock_position(&c, timer_us));
    }
    TEST_ASSERT_TRUE_MESSAGE(worst <= 6, "the clock drifted");
}

/* ----------------------------------------------------------- player */

/* A board in virtual time. The speaker holds the chunk that plays and one
 * more, and plays at exactly the pack's rate, like M5Unified's Speaker. */
typedef struct {
    uint64_t now_us;
    uint32_t rate;
    uint64_t given;          /* samples accepted */
    uint64_t play_start_us;  /* when the first sample began to play */
    int started;
    int base_draws, frame_draws, last_frame;
    int16_t heard[1400];
    /* Every frame draw: when, and which frame. */
    uint64_t draw_us[64];
    int draw_frame[64];
} board;

static uint64_t b_micros(void *ctx) { return ((board *)ctx)->now_us; }

static uint64_t b_played(const board *b)
{
    if (!b->started) return 0;
    uint64_t n = (b->now_us - b->play_start_us) * b->rate / 1000000u;
    return n > b->given ? b->given : n;
}

static uint32_t b_audio_write(void *ctx, const int16_t *samples, uint32_t n, uint32_t rate)
{
    board *b = (board *)ctx;
    (void)rate;
    /* Room for a chunk when less than one chunk waits behind the playing one. */
    if (b->started && b->given - b_played(b) > PN_CHUNK) return 0;
    if (!b->started) {
        b->started = 1;
        b->play_start_us = b->now_us;
    }
    memcpy(b->heard + b->given, samples, n * sizeof(int16_t));
    b->given += n;
    return n;
}

static void b_draw_base(void *ctx, const pn_pack *pack)
{
    (void)pack;
    ((board *)ctx)->base_draws++;
}

static void b_draw_frame(void *ctx, const pn_pack *pack, int frame)
{
    board *b = (board *)ctx;
    (void)pack;
    TEST_ASSERT_TRUE(b->frame_draws < 64);
    b->draw_us[b->frame_draws] = b->now_us;
    b->draw_frame[b->frame_draws] = frame;
    b->frame_draws++;
    b->last_frame = frame;
}

static void run_player(board *b, const pn_pack *k, int speaker, uint32_t loop_us)
{
    static pn_player player;
    pn_hal hal;
    memset(b, 0, sizeof *b);
    memset(&hal, 0, sizeof hal);
    b->rate = k->sample_rate;
    hal.ctx = b;
    hal.micros = b_micros;
    hal.audio_write = speaker ? b_audio_write : 0;
    hal.draw_base = b_draw_base;
    hal.draw_frame = b_draw_frame;
    hal.latency_samples = PN_CHUNK;
    pn_player_begin(&player, k, &hal);
    int guard = 0;
    while (pn_player_step(&player)) {
        b->now_us += loop_us;
        TEST_ASSERT_TRUE_MESSAGE(++guard < 100000, "the player never finished");
    }
    TEST_ASSERT_EQUAL_UINT32(k->sample_count, pn_player_position(&player));
}

/* The plan of the mono fixture: frame and start sample of each run. */
static const int PLAN_FRAME[5] = {0, 1, 2, 1, 0};
static const uint32_t PLAN_START[5] = {0, 200, 533, 600, 1000};

static void check_draws(const board *b, uint32_t rate, uint64_t t0, uint32_t slack_us)
{
    TEST_ASSERT_EQUAL_INT(1, b->base_draws);
    TEST_ASSERT_EQUAL_INT(5, b->frame_draws);  /* one draw per run, none in between */
    for (int i = 0; i < 5; i++) {
        TEST_ASSERT_EQUAL_INT(PLAN_FRAME[i], b->draw_frame[i]);
        uint64_t due = t0 + (uint64_t)PLAN_START[i] * 1000000u / rate;
        uint64_t at = b->draw_us[i];
        uint64_t late = at > due ? at - due : due - at;
        TEST_ASSERT_TRUE_MESSAGE(late <= slack_us, "a frame change is too far from the plan");
    }
}

static void test_player_follows_the_speaker(void)
{
    pn_pack k = open_mono();
    board b;
    run_player(&b, &k, 1, 500);
    /* Everything went to the speaker, in order, exactly once. */
    TEST_ASSERT_EQUAL_UINT64(1200, b.given);
    TEST_ASSERT_EQUAL_INT16_ARRAY(FIXTURE_PCM, b.heard, 1200);
    /* Each change within two loop passes (1 ms) of its place in the sound. */
    check_draws(&b, k.sample_rate, b.play_start_us, 1000);
}

static void test_player_follows_the_speaker_with_a_slow_loop(void)
{
    pn_pack k = open_mono();
    board b;
    run_player(&b, &k, 1, 7000);  /* 7 ms per pass */
    TEST_ASSERT_EQUAL_UINT64(1200, b.given);
    check_draws(&b, k.sample_rate, b.play_start_us, 14000);
}

static void test_player_without_a_speaker_follows_the_clock(void)
{
    pn_pack k = open_mono();
    board b;
    run_player(&b, &k, 0, 500);
    TEST_ASSERT_EQUAL_UINT64(0, b.given);
    check_draws(&b, k.sample_rate, 0, 500);
}

static void test_player_restarts(void)
{
    pn_pack k = open_mono();
    board b;
    run_player(&b, &k, 1, 500);
    run_player(&b, &k, 1, 500);
    check_draws(&b, k.sample_rate, b.play_start_us, 1000);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_open_reads_the_header);
    RUN_TEST(test_open_reads_a_colour_pack);
    RUN_TEST(test_open_rejects_bad_packs);
    RUN_TEST(test_plan_follows_the_runs);
    RUN_TEST(test_adpcm_matches_the_exporter);
    RUN_TEST(test_audio_seek);
    RUN_TEST(test_clock_without_a_speaker_follows_the_timer);
    RUN_TEST(test_clock_never_passes_what_was_submitted);
    RUN_TEST(test_clock_anchors_to_the_samples_played);
    RUN_TEST(test_player_follows_the_speaker);
    RUN_TEST(test_player_follows_the_speaker_with_a_slow_loop);
    RUN_TEST(test_player_without_a_speaker_follows_the_clock);
    RUN_TEST(test_player_restarts);
    return UNITY_END();
}
