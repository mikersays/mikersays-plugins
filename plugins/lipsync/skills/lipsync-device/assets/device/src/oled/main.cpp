// pixel-narrator on an ESP32 DevKit with a 128x64 1-bit OLED.
//
// The pack in packs/demo.oled.pnpk is embedded in the firmware. Its images
// are stored as the panel stores them (8-row pages, one byte per column),
// which is also the layout of U8g2's full frame buffer for SH1106 and
// SSD1306. The firmware copies pack bytes into that buffer and sends only
// the tiles that changed.
//
// Wiring, from the user's ESP32 sketches: SDA 21, SCL 22, address 0x3C.
// Build flags: PN_OLED_SH1106 (default) or PN_OLED_SSD1306 picks the
// controller. PN_I2S_SPEAKER adds a MAX98357A amplifier (BCLK 26, LRC 25,
// DIN 27); without it the board has no speaker and the frame follows the
// clock.
#include <Arduino.h>
#include <U8g2lib.h>
#include <Wire.h>

#include "pn_player.h"

#ifdef PN_I2S_SPEAKER
#include <driver/i2s.h>
#endif

extern const uint8_t pack_start[] asm("_binary_packs_demo_oled_pnpk_start");
extern const uint8_t pack_end[] asm("_binary_packs_demo_oled_pnpk_end");

namespace {

constexpr int PIN_SDA = 21, PIN_SCL = 22;
constexpr uint32_t PAUSE_MS = 1500;

#if defined(PN_OLED_SSD1306)
U8G2_SSD1306_128X64_NONAME_F_HW_I2C g_oled(U8G2_R0, U8X8_PIN_NONE, PIN_SCL, PIN_SDA);
#else
U8G2_SH1106_128X64_NONAME_F_HW_I2C g_oled(U8G2_R0, U8X8_PIN_NONE, PIN_SCL, PIN_SDA);
#endif

pn_pack g_pack;
pn_player g_player;

uint64_t halMicros(void *) { return (uint64_t)esp_timer_get_time(); }

// Copy a rectangle of page bytes into U8g2's buffer and send those tiles.
// The buffer holds 8 pages of 128 bytes; a tile is 8x8 pixels.
void push(const pn_rect &r, const uint8_t *pages)
{
    uint8_t *buf = g_oled.getBufferPtr();
    const uint16_t stride = g_oled.getBufferTileWidth() * 8;
    for (uint16_t page = 0; page < r.h / 8; page++)
        memcpy(buf + (r.y / 8 + page) * stride + r.x, pages + page * r.w, r.w);
    g_oled.updateDisplayArea(r.x / 8, r.y / 8, r.w / 8, r.h / 8);
}

void halDrawBase(void *, const pn_pack *pack) { push(pack->base, pack->base_image); }

void halDrawFrame(void *, const pn_pack *pack, int frame) { push(pack->mouth, pn_pack_frame(pack, frame)); }

#ifdef PN_I2S_SPEAKER
constexpr i2s_port_t I2S_PORT = I2S_NUM_0;
constexpr int PIN_BCLK = 26, PIN_LRC = 25, PIN_DIN = 27;
constexpr int DMA_BUFFERS = 4, DMA_SAMPLES = 128;  // The driver holds 512 samples.

void speakerBegin(uint32_t rate)
{
    i2s_config_t cfg = {};
    cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
    cfg.sample_rate = rate;
    cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
    cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
    cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    cfg.dma_buf_count = DMA_BUFFERS;
    cfg.dma_buf_len = DMA_SAMPLES;
    cfg.tx_desc_auto_clear = true;  // Silence, not a stuck buffer, when it runs dry.
    i2s_pin_config_t pins = {};
    pins.mck_io_num = I2S_PIN_NO_CHANGE;
    pins.bck_io_num = PIN_BCLK;
    pins.ws_io_num = PIN_LRC;
    pins.data_out_num = PIN_DIN;
    pins.data_in_num = I2S_PIN_NO_CHANGE;
    i2s_driver_install(I2S_PORT, &cfg, 0, nullptr);
    i2s_set_pin(I2S_PORT, &pins);
}

// A write with no wait takes what fits in the driver's buffers.
uint32_t halAudioWrite(void *, const int16_t *samples, uint32_t n, uint32_t)
{
    size_t written = 0;
    i2s_write(I2S_PORT, samples, n * sizeof(int16_t), &written, 0);
    return written / sizeof(int16_t);
}
#endif

const pn_hal g_hal = {
    nullptr, halMicros,
#ifdef PN_I2S_SPEAKER
    halAudioWrite,
#else
    nullptr,  // No speaker: pn_player follows the clock.
#endif
    halDrawBase, halDrawFrame,
#ifdef PN_I2S_SPEAKER
    DMA_BUFFERS * DMA_SAMPLES,
#else
    0,
#endif
    // One mouth frame is 18 tiles (144 bytes) over I2C at 400 kHz, about
    // 4 ms with the commands. An estimate: it was not measured, because
    // this firmware has not run on a device.
    4000,
};

bool g_playing = false;
uint32_t g_restartAt = 0;

}  // namespace

void setup()
{
    Serial.begin(115200);
    g_oled.setBusClock(400000);
    g_oled.begin();
    g_oled.clearBuffer();
    g_oled.sendBuffer();

    int err = pn_pack_open(&g_pack, pack_start, (uint32_t)(pack_end - pack_start));
    if (err == PN_OK && (g_pack.pixel_format != PN_PIX_MONO_VPAGE || g_pack.panel_w != 128 || g_pack.panel_h != 64))
        err = PN_ERR_FORMAT;
    if (err != PN_OK) {
        g_oled.setFont(u8g2_font_6x10_tr);
        g_oled.drawStr(0, 12, pn_error_text(err));
        g_oled.sendBuffer();
        Serial.printf("[narrator] %s\n", pn_error_text(err));
        g_pack.data = nullptr;
        return;
    }
#ifdef PN_I2S_SPEAKER
    speakerBegin(g_pack.sample_rate);
#endif
    pn_player_begin(&g_player, &g_pack, &g_hal);
    g_playing = true;
}

void loop()
{
    if (g_playing) {
        if (!pn_player_step(&g_player)) {
            g_playing = false;
            g_restartAt = millis() + PAUSE_MS;
        }
        return;
    }
    if (g_pack.data && millis() >= g_restartAt) {
        pn_player_begin(&g_player, &g_pack, &g_hal);
        g_playing = true;
    }
    delay(5);
}
