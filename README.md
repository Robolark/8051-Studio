# Robolark Embedded Studio

Supports:
- AT89S52 USBASP profile
- AT89S51 USBASP profile
- AT89C51 manual HEX profile
- STC89C52 serial ISP profile
- STC8 serial ISP profile
- Nuvoton W78E052DDG serial ISP/custom upload profile
- Custom 8051 profile
- SDCC compile and HEX generation
- Serial monitor
- Upload command manager
  
One-button flow:

Write C code -> Upload To Board

Internally:
1. Saves .c file
2. Compiles using bundled SDCC
3. Generates HEX using packihx
4. Runs the configured uploader command

Keep existing sdcc.zip in repo root.


```text
{hex}
{com}
{baud}
{chip}
{board}
```
