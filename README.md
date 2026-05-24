# Robolark 8051 Studio

Simple Windows application for writing 8051 C code and generating HEX files using bundled SDCC.

## GitHub Build Steps

1. Create a new GitHub repository.
2. Upload all files from this ZIP.
3. Download SDCC Windows version.
4. Copy SDCC files into:

```text
sdcc/
```

Recommended: upload the full SDCC folder contents, because SDCC may need include/lib files also.

Minimum required:

```text
sdcc/bin/sdcc.exe
sdcc/bin/packihx.exe
```

5. Go to GitHub repository.
6. Open **Actions**.
7. Select **Build Robolark 8051 Studio EXE**.
8. Click **Run workflow**.
9. After build completes, download artifact:

```text
Robolark_8051_Studio_EXE
```

Inside it you will get:

```text
Robolark_8051_Studio.exe
```