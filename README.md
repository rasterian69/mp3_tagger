# Audio Tools for macOS

A collection of Python scripts for managing audio files on macOS, optimized for working with NAS-mounted folders over a home network.

## Scripts

### 1. FLAC to MP3 Converter (`flac_to_mp3.py`)
### 2. MP3 Metadata Tagger (`mp3_tagger.py`)

---

## FLAC to MP3 Converter

Convert FLAC files to high-quality MP3 format while preserving metadata and folder structure.

### Features

- ✅ **High-quality conversion** - 320 kbps, 48 kHz, Joint Stereo, ID3v2.4
- ✅ **Recursive scanning** - Processes all subfolders
- ✅ **Preserves metadata** - Artist, album, title, year, genre, album art
- ✅ **Skip existing files** - Won't reconvert files that already exist
- ✅ **Moves original FLACs** - Organizes converted files into `converted_flac_to_be_deleted` folders
- ✅ **Error logging** - Tracks conversion failures with detailed logs
- ✅ **Dry-run mode** - Preview changes without modifying files
- ✅ **NAS-friendly** - Works seamlessly with SMB-mounted network drives
- ✅ **Native macOS UI** - Uses AppleScript folder picker

### Requirements

**System:**
- Python 3.8+
- FFmpeg (required for conversion)

Install FFmpeg:
```bash
brew install ffmpeg
```

**Python Dependencies:**
- Standard library only (no pip packages needed)

### Usage

```bash
python flac_to_mp3.py
```

**Workflow:**
1. Opens native macOS folder picker
2. Scans for all `.flac` files recursively
3. Shows summary of files found
4. Asks for confirmation to proceed
5. Prompts for dry-run mode
6. Converts each FLAC to MP3 (320 kbps)
7. Moves original FLAC to `converted_flac_to_be_deleted` folder in same directory
8. Displays final statistics

### Output Format

- **Format:** MPEG-1, Layer 3
- **Bit rate:** 320 kbps
- **Sample rate:** 48 kHz
- **Channels:** Joint Stereo
- **ID3 tag:** v2.4
- **Encoder:** LAME (via FFmpeg)

### Example

```
📂 Opening folder picker...
✅ Selected folder: /Volumes/NAS/Music/Albums

🔍 Scanning for FLAC files...

📊 SUMMARY
============================================================
Total FLAC files found: 47
Directories: 8

Proceed with conversion? (y/n): y
Dry-run mode (preview without converting)? (y/n): n

🚀 Starting conversion...

[1/47] Processing: Artist - Album/01 Track.flac
  🔄 Converting: 01 Track.flac
  ✅ SUCCESS: 01 Track.mp3
  📦 Moved: 01 Track.flac → converted_flac_to_be_deleted/

📈 FINAL RESULTS
============================================================
Total files: 47
✅ Successful: 47
⏭️  Skipped (already converted): 0
❌ Failed: 0

🎉 Conversion complete!
```

---

## MP3 Metadata Tagger

Comprehensive MP3 metadata editor with online lookup (MusicBrainz/Discogs) and bulk editing capabilities.

### Features

- ✅ **Bulk field editing** - Set Artist, Album, Year, Genre for all files at once
- ✅ **Bulk cover art upload** - Apply album art to multiple files instantly
- ✅ **Immediate application** - Changes are saved right away, no waiting
- ✅ **Online lookup** - MusicBrainz (free) with Discogs fallback
- ✅ **Manual editing** - Full control over every field
- ✅ **CSV export** - Before/after metadata snapshots
- ✅ **Cover art embedding** - Supports JPEG, PNG, GIF, BMP
- ✅ **Preserve existing tags** - Only updates fields you change
- ✅ **Error logging** - Detailed error tracking with timestamps
- ✅ **NAS-friendly** - No local database required
- ✅ **Native macOS UI** - AppleScript file/folder pickers

### Requirements

**System:**
- Python 3.8+
- macOS

**Python Dependencies:**
```bash
# Required
pip install mutagen

# Optional (for online lookup)
pip install musicbrainzngs python3-discogs-client requests
```

### Usage

```bash
python mp3_tagger.py
```

### Workflow

1. **Select folder** containing MP3 files
2. **View all files** found recursively
3. **Select files to tag** (individual, range, or all)
4. **Bulk editing** (optional):
   - Set Artist → Apply to all immediately
   - Set Album → Apply to all immediately
   - Set Year → Apply to all immediately
   - Set Genre → Apply to all immediately
5. **Bulk cover art** (optional):
   - Select image file
   - Choose which files to apply to
   - Applied immediately to selected files
6. **Choose**: Exit now or continue to individual editing
7. **Individual editing** (if needed):
   - Title and Track # for each file
   - Per-file overrides
8. **CSV exports** - Before/after metadata saved to logs

### Bulk Editing Features

#### Instant Application
When you enter a bulk value, you're immediately prompted:
```
Artist (for all files): The Beatles
  → Apply 'The Beatles' to all 12 files now? (y/n): y
  📝 Applying Artist to all files...
  ✅ Applied to 12 file(s)
```

Changes are written to disk **immediately** - no need to go through each file individually!

#### Bulk Cover Art
```
BULK ALBUM COVER ART
====================

Do you want to upload album cover art? (y/n): y
📁 Select cover art image...
✅ Cover art loaded!

Apply cover art to:
  [1] All selected files
  [2] Specific files (choose by number)
  [3] Cancel

Select option: 1
🎨 Applying cover art to 12 file(s)...
   Cover art size: 245678 bytes
✅ Cover art applied to 12 file(s)
```

### Online Lookup

**MusicBrainz** (no API key needed):
- Free and open database
- Excellent coverage for mainstream releases
- Automatically tried first

**Discogs** (optional API key):
- Great for rare releases and bootlegs
- Requires personal access token from: https://www.discogs.com/settings/developers
- Token stored in `~/.mp3_tagger_config.json`

### File Selection Examples

```
Select files: 1,3,5        # Individual files
Select files: 1-10         # Range
Select files: 1-5,8,10-12  # Mixed
Select files: all          # All files
```

### CSV Exports

All metadata is automatically exported to timestamped CSV files in `mp3_tagger_logs/`:

- `metadata_before_YYYYMMDD_HHMMSS.csv` - Original tags
- `metadata_after_bulk_YYYYMMDD_HHMMSS.csv` - After bulk edits (if exiting early)
- `metadata_after_YYYYMMDD_HHMMSS.csv` - Final tags after all edits
- `errors_YYYYMMDD_HHMMSS.log` - Error log (if any failures)

**CSV Columns:**
- filename
- artist
- album
- title
- track
- year
- genre
- bitrate
- duration

### Supported Tag Fields

- **Title** (TIT2)
- **Artist** (TPE1)
- **Album** (TALB)
- **Year** (TDRC)
- **Genre** (TCON)
- **Track #** (TRCK) - Simple format: 1, 2, 3...
- **Cover Art** (APIC) - Front cover, ID3v2.4

### Example Session

```
MP3 METADATA TAGGER for macOS
============================================================

📂 Opening folder picker...
✅ Selected folder: /Volumes/NAS/Music/Beatles

🔍 Scanning for MP3 files...

MP3 FILES FOUND
============================================================
  [  1] 01 Come Together.mp3
  [  2] 02 Something.mp3
  [  3] 03 Maxwell's Silver Hammer.mp3
  ...
  [ 12] 12 The End.mp3

Total: 12 file(s)

FILE SELECTION
============================================================
Enter file numbers to tag (e.g., '1,3,5' or '1-10' or 'all')

Select files: all
✅ Selected 12 file(s)

BULK EDITING OPTION
============================================================
Enable bulk editing? (y/n): y

BULK FIELD EDITING
============================================================

Artist (for all files): The Beatles
  → Apply 'The Beatles' to all 12 files now? (y/n): y
  📝 Applying Artist to all files...
  ✅ Applied to 12 file(s)

Album (for all files): Abbey Road
  → Apply 'Abbey Road' to all 12 files now? (y/n): y
  📝 Applying Album to all files...
  ✅ Applied to 12 file(s)

Year (for all files): 1969
  → Apply '1969' to all 12 files now? (y/n): y
  📝 Applying Year to all files...
  ✅ Applied to 12 file(s)

Genre (for all files): Rock
  → Apply 'Rock' to all 12 files now? (y/n): y
  📝 Applying Genre to all files...
  ✅ Applied to 12 file(s)

✅ Bulk changes applied to 12 file(s)

BULK ALBUM COVER ART
============================================================
Do you want to upload album cover art? (y/n): y
📁 Select cover art image...
✅ Cover art loaded!

Apply cover art to:
  [1] All selected files
  [2] Specific files (choose by number)
  [3] Cancel

Select option: 1
🎨 Applying cover art to 12 file(s)...
   Cover art size: 234567 bytes
✅ Cover art applied to 12 file(s)

BULK EDITING COMPLETE
============================================================
Your bulk changes have been applied to the selected files.

Options:
  [1] Done - Exit now (bulk changes already saved)
  [2] Continue to individual file editing (for Track #, Title, etc.)

Select option: 1

✅ Bulk editing complete!
📊 Exporting metadata...
✅ CSV exported: metadata_after_bulk_20251231_163045.csv (AFTER BULK EDIT)

🎉 All done!
============================================================
```

---

## Tips

### For FLAC Converter
- Run on albums that are complete and verified
- Use dry-run mode first to preview changes
- Original FLACs are moved, not deleted - safe to clean up later
- Works great with NAS folders over SMB

### For MP3 Tagger
- Use bulk editing for complete albums with consistent metadata
- Individual editing is great for mixtapes or compilations
- Online lookup works best with proper release names
- CSV exports help track changes and create backups
- Cover art supports common formats (JPEG, PNG, GIF, BMP)

---

## Error Handling

Both scripts:
- Skip files that can't be read/written
- Log all errors with timestamps
- Continue processing remaining files
- Display final statistics with success/fail counts

---

## Network Performance

Optimized for NAS usage:
- Minimal file I/O operations
- No temporary file creation
- Direct metadata writing
- Works over SMB, AFP, NFS

---

## License

MIT License - Feel free to use and modify as needed.

---

## Author

Created for macOS with 20+ years of Python scripting experience.

---

## Support

For issues or feature requests, please open an issue on GitHub.
