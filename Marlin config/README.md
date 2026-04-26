# Marlin Configuration

[Marlin 2.1.2.5](https://github.com/MarlinFirmware/Marlin/releases) configuration for the cylindrical 3D printer, based on a **BTT SKR V1.4 Turbo** board with **TMC2208** drivers. Uses Marlin's built-in **POLAR** kinematics mode to handle the cylindrical (X-linear + Y-rotational) axis layout.

Built with the [PlatformIO](https://marlinfw.org/docs/basics/auto_build_marlin.html) extension for VS Code. Example configurations for other boards can be found in the [MarlinFirmware/Configurations](https://github.com/MarlinFirmware/Configurations) repository.

## Key Changes from Stock

### `Configuration.h`

| Setting | Custom Value | Stock Default |
|---------|-------------|---------------|
| `MOTHERBOARD` | `BOARD_BTT_SKR_V1_4_TURBO` | RAMPS/other |
| `SERIAL_PORT` | `-1` (USB) | `0` |
| `X/Y/Z/E0_DRIVER_TYPE` | `TMC2208` | `A4988` |
| `POLAR` | enabled | disabled |
| `PRINTABLE_RADIUS` | `153.0` | — |
| `POLAR_FAST_RADIUS` | `3.0` | — |
| `POLAR_CENTER_OFFSET` | `0.0` | — |
| `FEEDRATE_SCALING` | enabled | disabled |
| `DEFAULT_AXIS_STEPS_PER_UNIT` | `{ 40, 71.50, 200, 72 }` | `{ 80, 80, 400, 500 }` |
| `TEMP_SENSOR_0` | `1` (Ender 3 V2 NTC) | `0` (disabled) |
| `X_BED_SIZE` / `Y_BED_SIZE` | `153` / `360` | `200` / `200` |
| `Y_MIN_POS` / `Y_MAX_POS` | `±999999` (unlimited rotation) | `0` / `200` |

The POLAR kinematics mode treats X as linear radial travel and Y as rotation in degrees. Y limits are set to ±999999 to allow unlimited rotation without endstop triggering.

### `Configuration_adv.h`

TMC2208 StealthChop enabled on all axes:
- `STEALTHCHOP_XY`, `STEALTHCHOP_Z`, `STEALTHCHOP_E` — all enabled
- Motor current: 800 mA on all axes

## Files

| File | Description |
|------|-------------|
| [Marlin-2.1.2.5/Marlin/Configuration.h](Marlin-2.1.2.5/Marlin/Configuration.h) | Primary machine configuration |
| [Marlin-2.1.2.5/Marlin/Configuration_adv.h](Marlin-2.1.2.5/Marlin/Configuration_adv.h) | Advanced configuration (TMC drivers) |