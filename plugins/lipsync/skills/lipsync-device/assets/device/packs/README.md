# packs

Each firmware embeds one pack from this folder. The folder ships empty.
Before you build, copy your packs here under these exact names, which
`platformio.ini` and the two `main.cpp` files refer to:

- `demo.oled.pnpk`: a pack for the 128x64 1-bit OLED (`--target oled`)
- `demo.sticks3.pnpk`: a pack for the M5Stack StickS3 (`--target sticks3`)

To change the line a device speaks, replace the file and build again.
