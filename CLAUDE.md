# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

PiInk - E-Ink picture frame using Pimoroni Inky Impression (4"/5.7"/7.3") on Raspberry Pi.

## Commands

```bash
sudo bash install.sh          # Install (run from piink directory)
sudo bash scripts/start.sh    # Start webserver
cat piink-log.txt             # View logs
lsof -i :80                   # Check if running
```

## Architecture

**Flask webserver** (`src/webserver.py`) on port 80:
- `GET /` - Web UI for uploads and settings
- `POST /` - Handle image uploads and actions
- `GET /uploads/<file>` - Serve uploaded images

**Key Files:**
- `src/webserver.py` - Main server, image processing, display control
- `src/generateInfo.py` - QR code info screen generator
- `config/settings.json` - Orientation, aspect ratio settings

## GPIO Buttons

BCM pins, active-low with pull-ups:

| Pin | Button | Function |
|-----|--------|----------|
| 5 | A | Display info/QR screen |
| 6 | B | Rotate image clockwise |
| 16 | C | Rotate image counter-clockwise |
| 24 | D | Reboot |

## cURL Upload

```bash
curl -X POST -F file=@image.png piink.local
```

## Privacy

Before committing, redact any personal info from uploaded images or screenshots.
