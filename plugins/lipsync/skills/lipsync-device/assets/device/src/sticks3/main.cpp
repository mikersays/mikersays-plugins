// pixel-narrator on the M5Stack StickS3: a face that speaks one line.
//
// The pack in packs/demo.sticks3.pnpk is embedded in the firmware. The
// player picks the mouth frame from the samples that the speaker has
// played. Button A (front) plays the line again.
//
// Board facts come from ~/git/stickos and ~/git/game-stickpet: the panel is
// a 135x240 ST7789 that M5Unified drives in RGB565, rotation 0 is portrait,
// the speaker hangs on an ES8311 codec, and volume above about 75% on
// battery can reset the board, so the volume stays at 150 of 255.
#include <M5Unified.h>

#include "pn_player.h"

extern const uint8_t pack_start[] asm("_binary_packs_demo_sticks3_pnpk_start");
extern const uint8_t pack_end[] asm("_binary_packs_demo_sticks3_pnpk_end");

namespace {

constexpr uint8_t VOLUME = 150;
constexpr uint32_t PAUSE_MS = 1500;  // Rest between two plays of the line.

pn_pack g_pack;
pn_player g_player;

// M5.Speaker keeps a pointer to the samples, not a copy, and holds the
// chunk that plays and one more. Three buffers in turn are never
// overwritten while it still reads them.
int16_t g_chunks[3][PN_CHUNK];
uint8_t g_next = 0;

uint64_t halMicros(void *) { return (uint64_t)esp_timer_get_time(); }

uint32_t halAudioWrite(void *, const int16_t *samples, uint32_t n, uint32_t rate)
{
    if (M5.Speaker.isPlaying(0) >= 2) return 0;  // Both slots are taken.
    int16_t *buf = g_chunks[g_next];
    g_next = (g_next + 1) % 3;
    memcpy(buf, samples, n * sizeof(int16_t));
    M5.Speaker.playRaw(buf, n, rate, false, 1, 0);
    return n;
}

// The pack stores RGB565 high byte first, which M5GFX calls swap565_t, so
// the pixels go to the panel as they are.
void push(const pn_rect &r, const uint8_t *pixels)
{
    M5.Display.pushImage(r.x, r.y, r.w, r.h, (const lgfx::swap565_t *)pixels);
}

void halDrawBase(void *, const pn_pack *pack) { push(pack->base, pack->base_image); }

void halDrawFrame(void *, const pn_pack *pack, int frame) { push(pack->mouth, pn_pack_frame(pack, frame)); }

const pn_hal g_hal = {
    nullptr, halMicros, halAudioWrite, halDrawBase, halDrawFrame,
    PN_CHUNK,  // The speaker holds one chunk besides the one that plays.
    // Two loop passes and one mouth frame over SPI. An estimate: it was not
    // measured, because this firmware has not run on a device.
    2700,
};

bool g_playing = false;
uint32_t g_restartAt = 0;

void fail(const char *msg)
{
    M5.Display.fillScreen(TFT_BLACK);
    M5.Display.setTextColor(TFT_RED);
    M5.Display.drawString(msg, 4, 4);
    Serial.printf("[narrator] %s\n", msg);
}

}  // namespace

void setup()
{
    auto cfg = M5.config();
    cfg.serial_baudrate = 115200;
    cfg.output_power = false;  // No 5 V on Grove or the Hat port (as StickOS).
    M5.begin(cfg);
    M5.Display.setRotation(0);  // Portrait, 135 wide and 240 high.
    M5.Display.setBrightness(100);
    M5.Speaker.begin();
    M5.Speaker.setVolume(VOLUME);

    int err = pn_pack_open(&g_pack, pack_start, (uint32_t)(pack_end - pack_start));
    if (err != PN_OK) {
        fail(pn_error_text(err));
        return;
    }
    if (g_pack.pixel_format != PN_PIX_RGB565_BE || g_pack.panel_w != M5.Display.width() ||
        g_pack.panel_h != M5.Display.height()) {
        fail("pack is for another panel");
        return;
    }
    pn_player_begin(&g_player, &g_pack, &g_hal);
    g_playing = true;
}

void loop()
{
    M5.update();
    if (g_playing) {
        if (!pn_player_step(&g_player)) {
            g_playing = false;
            g_restartAt = millis() + PAUSE_MS;
        }
        return;
    }
    if (!g_pack.data) return;
    if (M5.BtnA.wasPressed() || (g_restartAt && millis() >= g_restartAt)) {
        pn_player_begin(&g_player, &g_pack, &g_hal);
        g_playing = true;
    }
    delay(5);
}
