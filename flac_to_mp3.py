#!/usr/bin/env python3
"""
FLAC to MP3 Folder Converter for macOS
Converts FLAC files to 320kbps MP3 while preserving metadata and album art.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


def check_ffmpeg():
    """Check if FFmpeg is installed and accessible."""
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n❌ ERROR: FFmpeg is not installed or not found in PATH")
        print("\nTo install FFmpeg on macOS, run:")
        print("    brew install ffmpeg")
        print("\nIf you don't have Homebrew, install it from: https://brew.sh")
        return False


def select_folder_macos():
    """Open native macOS folder picker dialog."""
    applescript = '''
    tell application "System Events"
        activate
        set folderPath to choose folder with prompt "Select folder containing FLAC files:"
        return POSIX path of folderPath
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True
        )
        folder_path = result.stdout.strip()
        return folder_path if folder_path else None
    except subprocess.CalledProcessError:
        print("\n⚠️  Folder selection cancelled")
        return None


def find_flac_files(root_dir):
    """Recursively find all FLAC files in directory."""
    flac_files = []
    root_path = Path(root_dir)
    
    for flac_file in root_path.rglob('*.flac'):
        if flac_file.is_file():
            flac_files.append(flac_file)
    
    return sorted(flac_files)


def get_mp3_path(flac_path):
    """Get corresponding MP3 path for a FLAC file."""
    return flac_path.with_suffix('.mp3')


def get_converted_folder(flac_path):
    """Get the converted_flac_to_be_deleted folder in the same directory."""
    return flac_path.parent / 'converted_flac_to_be_deleted'


def convert_flac_to_mp3(flac_path, dry_run=False):
    """
    Convert a FLAC file to MP3 (320kbps, 48kHz, Joint Stereo).
    Preserves metadata and album art.
    Returns (success, error_message).
    """
    mp3_path = get_mp3_path(flac_path)
    
    # Skip if MP3 already exists
    if mp3_path.exists():
        print(f"  ⏭️  SKIP: {mp3_path.name} (already exists)")
        return True, None
    
    if dry_run:
        print(f"  [DRY-RUN] Would convert: {flac_path.name} → {mp3_path.name}")
        return True, None
    
    print(f"  🔄 Converting: {flac_path.name}")
    
    try:
        # FFmpeg command for high-quality MP3 conversion
        # -i: input file
        # -vn: no video (in case of embedded album art)
        # -ar 48000: 48kHz sample rate
        # -ac 2: 2 channels (stereo)
        # -b:a 320k: 320 kbps bitrate
        # -id3v2_version 4: ID3v2.4 tags
        # -map_metadata 0: copy all metadata
        # -map 0: copy album art and all streams
        cmd = [
            'ffmpeg',
            '-i', str(flac_path),
            '-vn',
            '-ar', '48000',
            '-ac', '2',
            '-b:a', '320k',
            '-id3v2_version', '4',
            '-map_metadata', '0',
            '-map', '0',
            '-y',  # Overwrite without asking
            str(mp3_path)
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        print(f"  ✅ SUCCESS: {mp3_path.name}")
        return True, None
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='ignore')
        print(f"  ❌ FAILED: {flac_path.name}")
        return False, error_msg


def move_flac_to_converted(flac_path, dry_run=False):
    """Move FLAC file to converted_flac_to_be_deleted folder."""
    converted_folder = get_converted_folder(flac_path)
    
    if dry_run:
        print(f"  [DRY-RUN] Would move: {flac_path.name} → {converted_folder}/")
        return True, None
    
    try:
        # Create folder if it doesn't exist
        converted_folder.mkdir(exist_ok=True)
        
        # Move the file
        destination = converted_folder / flac_path.name
        shutil.move(str(flac_path), str(destination))
        
        print(f"  📦 Moved: {flac_path.name} → converted_flac_to_be_deleted/")
        return True, None
        
    except Exception as e:
        error_msg = f"Failed to move file: {str(e)}"
        print(f"  ⚠️  WARNING: Could not move {flac_path.name}")
        return False, error_msg


def log_error(flac_path, error_message):
    """Log conversion errors to a file in the converted folder."""
    converted_folder = get_converted_folder(flac_path)
    converted_folder.mkdir(exist_ok=True)
    
    log_file = converted_folder / 'conversion_errors.log'
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"\n[{timestamp}] {flac_path.name}\n{error_message}\n{'-'*80}\n"
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"  ⚠️  Could not write to log file: {e}")


def show_summary(flac_files):
    """Display summary of files to be processed."""
    if not flac_files:
        print("\n📭 No FLAC files found in the selected folder.")
        return
    
    # Group files by directory
    dirs = {}
    for flac in flac_files:
        parent = flac.parent
        if parent not in dirs:
            dirs[parent] = []
        dirs[parent].append(flac)
    
    print(f"\n📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Total FLAC files found: {len(flac_files)}")
    print(f"Directories: {len(dirs)}")
    print(f"\nFiles by directory:")
    
    for directory, files in sorted(dirs.items()):
        print(f"\n  📁 {directory}")
        print(f"     {len(files)} file(s)")


def get_user_confirmation():
    """Ask user to confirm proceeding with conversion."""
    while True:
        response = input("\nProceed with conversion? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")


def ask_dry_run():
    """Ask user if they want to run in dry-run mode."""
    while True:
        response = input("\nDry-run mode (preview without converting)? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")


def main():
    """Main execution function."""
    print("=" * 60)
    print("  FLAC to MP3 Converter for macOS")
    print("=" * 60)
    
    # Check for FFmpeg
    if not check_ffmpeg():
        sys.exit(1)
    
    # Select folder
    print("\n📂 Opening folder picker...")
    selected_folder = select_folder_macos()
    
    if not selected_folder:
        print("\n👋 Goodbye!")
        sys.exit(0)
    
    print(f"\n✅ Selected folder: {selected_folder}")
    
    # Find FLAC files
    print("\n🔍 Scanning for FLAC files...")
    flac_files = find_flac_files(selected_folder)
    
    if not flac_files:
        print("\n📭 No FLAC files found in the selected folder.")
        sys.exit(0)
    
    # Show summary
    show_summary(flac_files)
    
    # Get confirmation
    if not get_user_confirmation():
        print("\n🚫 Operation cancelled by user")
        sys.exit(0)
    
    # Ask about dry-run mode
    dry_run = ask_dry_run()
    
    if dry_run:
        print("\n🔍 DRY-RUN MODE - No files will be modified")
    
    # Process files
    print(f"\n{'='*60}")
    print("🚀 Starting conversion...")
    print(f"{'='*60}\n")
    
    total = len(flac_files)
    successful = 0
    skipped = 0
    failed = 0
    
    for idx, flac_path in enumerate(flac_files, 1):
        print(f"\n[{idx}/{total}] Processing: {flac_path.relative_to(selected_folder)}")
        
        # Check if already converted
        mp3_path = get_mp3_path(flac_path)
        if mp3_path.exists():
            skipped += 1
            print(f"  ⏭️  SKIP: MP3 already exists")
            continue
        
        # Convert to MP3
        success, error = convert_flac_to_mp3(flac_path, dry_run)
        
        if success and not dry_run:
            # Move FLAC to converted folder
            move_success, move_error = move_flac_to_converted(flac_path, dry_run)
            
            if move_success:
                successful += 1
            else:
                # Conversion worked but move failed
                successful += 1
                if move_error:
                    log_error(flac_path, f"Move failed: {move_error}")
        elif success and dry_run:
            successful += 1
        else:
            failed += 1
            if error:
                log_error(flac_path, error)
    
    # Final summary
    print(f"\n{'='*60}")
    print("📈 FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Total files: {total}")
    print(f"✅ Successful: {successful}")
    print(f"⏭️  Skipped (already converted): {skipped}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print(f"\n⚠️  Check conversion_errors.log files in converted_flac_to_be_deleted folders")
    
    if dry_run:
        print(f"\n🔍 DRY-RUN completed - no files were modified")
    else:
        print(f"\n🎉 Conversion complete!")
    
    print(f"{'='*60}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
