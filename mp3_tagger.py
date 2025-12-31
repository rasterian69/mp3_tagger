#!/usr/bin/env python3
"""
MP3 Tagger for macOS
Comprehensive MP3 metadata editor with online lookup capabilities.
Supports MusicBrainz and Discogs API integration.
"""

import os
import sys
import subprocess
import json
import requests
from pathlib import Path
from datetime import datetime
from io import BytesIO

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TRCK, APIC
except ImportError:
    print("\n❌ ERROR: mutagen library not installed")
    print("Install it with: pip install mutagen")
    sys.exit(1)

try:
    import musicbrainzngs
    MUSICBRAINZ_AVAILABLE = True
except ImportError:
    print("\n⚠️  WARNING: musicbrainzngs not installed (MusicBrainz lookup disabled)")
    print("Install it with: pip install musicbrainzngs")
    MUSICBRAINZ_AVAILABLE = False

try:
    import discogs_client
    DISCOGS_AVAILABLE = True
except ImportError:
    print("\n⚠️  WARNING: discogs_client not installed (Discogs lookup disabled)")
    print("Install it with: pip install python3-discogs-client")
    DISCOGS_AVAILABLE = False


# Configuration
CONFIG_FILE = Path.home() / '.mp3_tagger_config.json'
USER_AGENT = 'MP3Tagger/1.0'


class Config:
    """Manage configuration settings."""
    
    def __init__(self):
        self.discogs_token = None
        self.load()
    
    def load(self):
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.discogs_token = data.get('discogs_token')
            except Exception as e:
                print(f"⚠️  Could not load config: {e}")
    
    def save(self):
        """Save configuration to file."""
        try:
            data = {'discogs_token': self.discogs_token}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save config: {e}")
    
    def setup_discogs(self):
        """Prompt for Discogs token if not configured."""
        if not DISCOGS_AVAILABLE:
            return False
        
        if self.discogs_token:
            return True
        
        print("\n🔑 Discogs API Token Setup")
        print("To use Discogs lookup, you need a personal access token.")
        print("Get one at: https://www.discogs.com/settings/developers")
        
        response = input("\nDo you want to configure Discogs now? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            token = input("Enter your Discogs token: ").strip()
            if token:
                self.discogs_token = token
                self.save()
                print("✅ Discogs token saved!")
                return True
        
        return False


def select_folder_macos():
    """Open native macOS folder picker dialog."""
    applescript = '''
    tell application "System Events"
        activate
        set folderPath to choose folder with prompt "Select folder containing MP3 files:"
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


def find_mp3_files(root_dir):
    """Recursively find all MP3 files in directory."""
    mp3_files = []
    root_path = Path(root_dir)
    
    for mp3_file in root_path.rglob('*.mp3'):
        if mp3_file.is_file():
            mp3_files.append(mp3_file)
    
    return sorted(mp3_files)


def read_mp3_metadata(file_path):
    """
    Read metadata from MP3 file.
    Returns dict with current tags or None if error.
    """
    try:
        audio = MP3(file_path, ID3=ID3)
        
        # Try to add ID3 tag if it doesn't exist
        if audio.tags is None:
            audio.add_tags()
        
        tags = audio.tags
        
        metadata = {
            'title': str(tags.get('TIT2', [''])[0]) if 'TIT2' in tags else '',
            'artist': str(tags.get('TPE1', [''])[0]) if 'TPE1' in tags else '',
            'album': str(tags.get('TALB', [''])[0]) if 'TALB' in tags else '',
            'year': str(tags.get('TDRC', [''])[0]) if 'TDRC' in tags else '',
            'genre': str(tags.get('TCON', [''])[0]) if 'TCON' in tags else '',
            'track': str(tags.get('TRCK', [''])[0]) if 'TRCK' in tags else '',
            'duration': audio.info.length,
            'bitrate': audio.info.bitrate,
            'has_cover': 'APIC:' in tags or any(k.startswith('APIC') for k in tags.keys())
        }
        
        return metadata
        
    except Exception as e:
        return None


def write_mp3_metadata(file_path, metadata, cover_art_data=None):
    """
    Write metadata to MP3 file.
    Returns (success, error_message).
    """
    try:
        audio = MP3(file_path, ID3=ID3)
        
        if audio.tags is None:
            audio.add_tags()
        
        tags = audio.tags
        
        # Write text tags
        if metadata.get('title'):
            tags['TIT2'] = TIT2(encoding=3, text=metadata['title'])
        
        if metadata.get('artist'):
            tags['TPE1'] = TPE1(encoding=3, text=metadata['artist'])
        
        if metadata.get('album'):
            tags['TALB'] = TALB(encoding=3, text=metadata['album'])
        
        if metadata.get('year'):
            tags['TDRC'] = TDRC(encoding=3, text=metadata['year'])
        
        if metadata.get('genre'):
            tags['TCON'] = TCON(encoding=3, text=metadata['genre'])
        
        if metadata.get('track'):
            tags['TRCK'] = TRCK(encoding=3, text=metadata['track'])
        
        # Write cover art if provided
        if cover_art_data:
            # Detect MIME type from image data
            mime_type = 'image/jpeg'
            if cover_art_data[:4] == b'\x89PNG':
                mime_type = 'image/png'
            elif cover_art_data[:3] == b'GIF':
                mime_type = 'image/gif'
            elif cover_art_data[:2] == b'BM':
                mime_type = 'image/bmp'
            
            # Remove existing album art first
            tags.delall('APIC')
            
            # Add new album art
            tags['APIC'] = APIC(
                encoding=3,
                mime=mime_type,
                type=3,  # Cover (front)
                desc='Cover',
                data=cover_art_data
            )
        
        audio.save(v2_version=4)
        return True, None
        
    except Exception as e:
        return False, str(e)


def search_musicbrainz(query, search_type='recording'):
    """
    Search MusicBrainz for metadata.
    search_type: 'recording', 'release', or 'artist'
    Returns list of results.
    """
    if not MUSICBRAINZ_AVAILABLE:
        return []
    
    try:
        musicbrainzngs.set_useragent('MP3Tagger', '1.0', 'https://github.com/user/mp3tagger')
        
        results = []
        
        if search_type == 'recording':
            search_results = musicbrainzngs.search_recordings(query=query, limit=10)
            for recording in search_results.get('recording-list', []):
                artist = recording.get('artist-credit-phrase', 'Unknown Artist')
                title = recording.get('title', 'Unknown Title')
                
                # Get release info if available
                album = ''
                year = ''
                if 'release-list' in recording and recording['release-list']:
                    release = recording['release-list'][0]
                    album = release.get('title', '')
                    if 'date' in release:
                        year = release['date'][:4]
                
                results.append({
                    'source': 'MusicBrainz',
                    'artist': artist,
                    'title': title,
                    'album': album,
                    'year': year,
                    'score': recording.get('ext:score', '0')
                })
        
        elif search_type == 'release':
            search_results = musicbrainzngs.search_releases(query=query, limit=10)
            for release in search_results.get('release-list', []):
                artist = release.get('artist-credit-phrase', 'Unknown Artist')
                album = release.get('title', 'Unknown Album')
                year = ''
                if 'date' in release:
                    year = release['date'][:4]
                
                results.append({
                    'source': 'MusicBrainz',
                    'artist': artist,
                    'album': album,
                    'year': year,
                    'score': release.get('ext:score', '0')
                })
        
        return results
        
    except Exception as e:
        print(f"  ⚠️  MusicBrainz error: {e}")
        return []


def search_discogs(query, config, search_type='release'):
    """
    Search Discogs for metadata.
    search_type: 'release' or 'artist'
    Returns list of results.
    """
    if not DISCOGS_AVAILABLE or not config.discogs_token:
        return []
    
    try:
        d = discogs_client.Client(USER_AGENT, user_token=config.discogs_token)
        
        results = []
        search_results = d.search(query, type=search_type)
        
        for item in search_results[:10]:
            if search_type == 'release':
                artist = ', '.join([a.name for a in item.artists]) if hasattr(item, 'artists') else 'Unknown Artist'
                album = item.title if hasattr(item, 'title') else 'Unknown Album'
                year = str(item.year) if hasattr(item, 'year') and item.year else ''
                
                results.append({
                    'source': 'Discogs',
                    'artist': artist,
                    'album': album,
                    'year': year,
                    'discogs_id': item.id
                })
        
        return results
        
    except Exception as e:
        print(f"  ⚠️  Discogs error: {e}")
        return []


def download_cover_art(url):
    """Download cover art from URL. Returns image data or None."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        print(f"  ⚠️  Cover art download failed: {e}")
        return None


def select_cover_art_file():
    """Open macOS file picker for cover art selection."""
    applescript = '''
    tell application "System Events"
        activate
        set imageFile to choose file with prompt "Select cover art image:" of type {"public.image"}
        return POSIX path of imageFile
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True
        )
        file_path = result.stdout.strip()
        if file_path and Path(file_path).exists():
            with open(file_path, 'rb') as f:
                return f.read()
        return None
    except subprocess.CalledProcessError:
        return None


def display_file_list(files, root_dir):
    """Display list of MP3 files with index numbers."""
    print(f"\n{'='*80}")
    print("MP3 FILES FOUND")
    print(f"{'='*80}")
    
    for idx, file_path in enumerate(files, 1):
        relative_path = file_path.relative_to(root_dir)
        print(f"  [{idx:3d}] {relative_path}")
    
    print(f"\nTotal: {len(files)} file(s)")


def select_files_to_tag(files):
    """
    Prompt user to select which files to tag.
    Returns list of selected file paths.
    """
    print("\n" + "="*80)
    print("FILE SELECTION")
    print("="*80)
    print("Enter file numbers to tag (e.g., '1,3,5' or '1-10' or 'all')")
    
    while True:
        selection = input("\nSelect files: ").strip().lower()
        
        if selection == 'all':
            return files
        
        try:
            selected_indices = set()
            
            # Parse selection
            parts = selection.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    # Range
                    start, end = part.split('-')
                    start = int(start.strip())
                    end = int(end.strip())
                    selected_indices.update(range(start, end + 1))
                else:
                    # Single number
                    selected_indices.add(int(part))
            
            # Validate indices
            valid_indices = set(range(1, len(files) + 1))
            if not selected_indices.issubset(valid_indices):
                print(f"❌ Invalid file numbers. Must be between 1 and {len(files)}")
                continue
            
            # Return selected files
            selected_files = [files[i-1] for i in sorted(selected_indices)]
            print(f"\n✅ Selected {len(selected_files)} file(s)")
            return selected_files
            
        except ValueError:
            print("❌ Invalid input. Use format: '1,3,5' or '1-10' or 'all'")


def bulk_edit_fields(selected_files):
    """
    Bulk edit common fields and apply to all selected files immediately.
    Returns dict with bulk values that were applied.
    """
    print(f"\n{'='*80}")
    print("BULK FIELD EDITING")
    print(f"{'='*80}")
    print("\nSet common values for all selected files.")
    print("You'll be prompted to apply each field immediately.")
    print("Press Enter to skip a field (edit individually per file).")
    
    bulk_applied = {}
    applied_count = 0
    
    fields = [
        ('artist', 'Artist'),
        ('album', 'Album'),
        ('year', 'Year'),
        ('genre', 'Genre')
    ]
    
    for field_key, field_label in fields:
        value = input(f"\n{field_label} (for all files): ").strip()
        
        if not value:
            continue
        
        # Ask to apply immediately
        response = input(f"  → Apply '{value}' to all {len(selected_files)} files now? (y/n): ").strip().lower()
        
        if response in ['y', 'yes']:
            print(f"  📝 Applying {field_label} to all files...")
            
            success_count = 0
            fail_count = 0
            
            for file_path in selected_files:
                try:
                    # Read current metadata
                    metadata = read_mp3_metadata(file_path)
                    if metadata is None:
                        fail_count += 1
                        continue
                    
                    # Update only this field
                    metadata[field_key] = value
                    
                    # Write back
                    success, error = write_mp3_metadata(file_path, metadata)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                        
                except Exception as e:
                    fail_count += 1
            
            if success_count > 0:
                print(f"  ✅ Applied to {success_count} file(s)")
                bulk_applied[field_key] = value
                applied_count += 1
            
            if fail_count > 0:
                print(f"  ⚠️  Failed: {fail_count} file(s)")
        else:
            print(f"  ⏭️  Skipped - will edit individually")
    
    # Show summary
    if bulk_applied:
        print(f"\n✅ Bulk changes applied to {len(selected_files)} file(s):")
        for field, value in bulk_applied.items():
            print(f"   {field.capitalize()}: {value}")
    else:
        print("\n⚠️  No bulk changes applied (will edit each file individually)")
    
    return bulk_applied


def bulk_cover_art_upload(selected_files, root_dir):
    """
    Upload album cover art and apply immediately to selected files.
    Returns dict mapping file paths to cover art data (for tracking).
    """
    print(f"\n{'='*80}")
    print("BULK ALBUM COVER ART")
    print(f"{'='*80}")
    
    response = input("\nDo you want to upload album cover art? (y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        return {}
    
    # Select cover art file
    print("\n📁 Select cover art image...")
    cover_art_data = select_cover_art_file()
    
    if not cover_art_data:
        print("⚠️  No cover art selected")
        return {}
    
    print("✅ Cover art loaded!")
    
    # Ask which files to apply to
    print("\nApply cover art to:")
    print("  [1] All selected files")
    print("  [2] Specific files (choose by number)")
    print("  [3] Cancel")
    
    choice = input("\nSelect option: ").strip()
    
    files_to_update = []
    
    if choice == '1':
        # Apply to all
        files_to_update = selected_files
    
    elif choice == '2':
        # Select specific files
        print(f"\n{'='*80}")
        print("SELECT FILES FOR COVER ART")
        print(f"{'='*80}")
        
        for idx, file_path in enumerate(selected_files, 1):
            relative_path = file_path.relative_to(root_dir)
            print(f"  [{idx:3d}] {relative_path}")
        
        print("\nEnter file numbers (e.g., '1,3,5' or '1-10' or 'all')")
        
        while True:
            selection = input("\nSelect files: ").strip().lower()
            
            if selection == 'all':
                files_to_update = selected_files
                break
            
            try:
                selected_indices = set()
                
                # Parse selection
                parts = selection.split(',')
                for part in parts:
                    part = part.strip()
                    if '-' in part:
                        # Range
                        start, end = part.split('-')
                        start = int(start.strip())
                        end = int(end.strip())
                        selected_indices.update(range(start, end + 1))
                    else:
                        # Single number
                        selected_indices.add(int(part))
                
                # Validate indices
                valid_indices = set(range(1, len(selected_files) + 1))
                if not selected_indices.issubset(valid_indices):
                    print(f"❌ Invalid file numbers. Must be between 1 and {len(selected_files)}")
                    continue
                
                # Get selected files
                files_to_update = [selected_files[i-1] for i in sorted(selected_indices)]
                break
                
            except ValueError:
                print("❌ Invalid input. Use format: '1,3,5' or '1-10' or 'all'")
    
    else:
        print("\n⏭️  Cover art upload cancelled")
        return {}
    
    # Apply cover art immediately
    if not files_to_update:
        return {}
    
    print(f"\n🎨 Applying cover art to {len(files_to_update)} file(s)...")
    print(f"   Cover art size: {len(cover_art_data)} bytes")
    
    success_count = 0
    fail_count = 0
    cover_mapping = {}
    
    for file_path in files_to_update:
        try:
            # Read current metadata
            metadata = read_mp3_metadata(file_path)
            if metadata is None:
                print(f"   ❌ Could not read: {file_path.name}")
                fail_count += 1
                continue
            
            # Write cover art only (pass existing metadata to preserve it)
            success, error = write_mp3_metadata(file_path, metadata, cover_art_data)
            if success:
                success_count += 1
                cover_mapping[str(file_path)] = cover_art_data
            else:
                print(f"   ❌ Failed to write: {file_path.name} - {error}")
                fail_count += 1
                
        except Exception as e:
            print(f"   ❌ Exception: {file_path.name} - {str(e)}")
            fail_count += 1
    
    if success_count > 0:
        print(f"✅ Cover art applied to {success_count} file(s)")
    
    if fail_count > 0:
        print(f"⚠️  Failed: {fail_count} file(s)")
    
    return cover_mapping


def edit_metadata_interactive(file_path, existing_metadata, bulk_values=None, bulk_cover_art=None):
    """
    Interactive metadata editor for a single file.
    Returns dict with new metadata, or None to skip.
    """
    print(f"\n{'='*80}")
    print(f"EDITING: {file_path.name}")
    print(f"{'='*80}")
    
    if existing_metadata:
        has_bulk_cover = bulk_cover_art is not None
        cover_status = 'Yes'
        if existing_metadata.get('has_cover'):
            cover_status = 'Yes'
        elif has_bulk_cover:
            cover_status = 'Yes [BULK]'
        else:
            cover_status = 'No'
        
        print("\nCurrent metadata:")
        print(f"  Title:  {existing_metadata.get('title', '(none)')}")
        print(f"  Artist: {existing_metadata.get('artist', '(none)')}")
        print(f"  Album:  {existing_metadata.get('album', '(none)')}")
        print(f"  Year:   {existing_metadata.get('year', '(none)')}")
        print(f"  Genre:  {existing_metadata.get('genre', '(none)')}")
        print(f"  Track:  {existing_metadata.get('track', '(none)')}")
        print(f"  Cover:  {cover_status}")
    else:
        print("\n⚠️  Could not read existing metadata")
        existing_metadata = {}
    
    # Menu
    print("\nOptions:")
    print("  [1] Online lookup (MusicBrainz/Discogs)")
    print("  [2] Manual edit")
    print("  [3] Skip this file")
    
    choice = input("\nSelect option: ").strip()
    
    if choice == '1':
        return lookup_and_edit(file_path, existing_metadata, bulk_values, bulk_cover_art)
    elif choice == '2':
        return manual_edit(existing_metadata, bulk_values, bulk_cover_art)
    elif choice == '3':
        return None
    else:
        print("❌ Invalid choice")
        return edit_metadata_interactive(file_path, existing_metadata, bulk_values, bulk_cover_art)


def lookup_and_edit(file_path, existing_metadata, bulk_values=None, bulk_cover_art=None):
    """Perform online lookup and let user select/edit results."""
    
    if bulk_values is None:
        bulk_values = {}
    
    # Get search query
    default_query = existing_metadata.get('artist', '') or existing_metadata.get('album', '') or file_path.stem
    print(f"\nDefault search query: {default_query}")
    query = input("Enter search query (or press Enter to use default): ").strip()
    
    if not query:
        query = default_query
    
    print(f"\n🔍 Searching for: {query}")
    
    # Search MusicBrainz first
    results = []
    if MUSICBRAINZ_AVAILABLE:
        print("  → Searching MusicBrainz...")
        mb_results = search_musicbrainz(query, 'release')
        results.extend(mb_results)
    
    # Fallback to Discogs if no MusicBrainz results
    if not results:
        print("  → No MusicBrainz results, trying Discogs...")
        config = Config()
        if config.discogs_token:
            discogs_results = search_discogs(query, config, 'release')
            results.extend(discogs_results)
    
    if not results:
        print("\n❌ No results found")
        print("\nOptions:")
        print("  [1] Try different search")
        print("  [2] Manual edit")
        print("  [3] Skip this file")
        
        choice = input("\nSelect option: ").strip()
        if choice == '1':
            return lookup_and_edit(file_path, existing_metadata, bulk_values, bulk_cover_art)
        elif choice == '2':
            return manual_edit(existing_metadata, bulk_values, bulk_cover_art)
        else:
            return None
    
    # Display results
    print(f"\n{'='*80}")
    print(f"SEARCH RESULTS ({len(results)} found)")
    print(f"{'='*80}")
    
    for idx, result in enumerate(results, 1):
        print(f"\n[{idx}] {result['source']}")
        print(f"    Artist: {result.get('artist', 'N/A')}")
        print(f"    Album:  {result.get('album', 'N/A')}")
        print(f"    Year:   {result.get('year', 'N/A')}")
    
    print(f"\n[0] Manual edit instead")
    
    # Select result
    while True:
        try:
            selection = input("\nSelect result (or 0 for manual): ").strip()
            idx = int(selection)
            
            if idx == 0:
                return manual_edit(existing_metadata)
            
            if 1 <= idx <= len(results):
                selected = results[idx - 1]
                
                # Populate metadata from selected result, with bulk values taking priority
                new_metadata = {
                    'title': existing_metadata.get('title', ''),
                    'artist': bulk_values.get('artist') or selected.get('artist', ''),
                    'album': bulk_values.get('album') or selected.get('album', ''),
                    'year': bulk_values.get('year') or selected.get('year', ''),
                    'genre': bulk_values.get('genre') or existing_metadata.get('genre', ''),
                    'track': existing_metadata.get('track', '')
                }
                
                # Allow manual editing of the populated data
                print("\n✅ Selected result. You can now edit the fields:")
                return manual_edit(new_metadata, bulk_values)
            else:
                print(f"❌ Invalid selection. Enter 0-{len(results)}")
                
        except ValueError:
            print("❌ Invalid input. Enter a number.")


def manual_edit(existing_metadata, bulk_values=None, bulk_cover_art=None):
    """Manual metadata editor. Returns dict with new metadata."""
    
    if bulk_values is None:
        bulk_values = {}
    
    print(f"\n{'='*80}")
    print("MANUAL METADATA EDIT")
    print(f"{'='*80}")
    print("Press Enter to keep existing value, or type new value")
    
    # Show bulk values if any
    active_bulk = {k: v for k, v in bulk_values.items() if v}
    if active_bulk:
        print("\n💡 Bulk values set (will be used if you press Enter):")
        for field, value in active_bulk.items():
            print(f"   {field.capitalize()}: {value}")
    
    if bulk_cover_art is not None:
        print("\n🎨 Bulk cover art will be applied (uploaded earlier)")
    
    new_metadata = {}
    
    # Title
    current = existing_metadata.get('title', '')
    new_value = input(f"\nTitle [{current}]: ").strip()
    new_metadata['title'] = new_value if new_value else current
    
    # Artist - use bulk value if set and user presses Enter
    bulk_artist = bulk_values.get('artist', '')
    current = bulk_artist or existing_metadata.get('artist', '')
    prompt = f"Artist [{current}]" + (" [BULK]" if bulk_artist else "")
    new_value = input(f"{prompt}: ").strip()
    new_metadata['artist'] = new_value if new_value else current
    
    # Album - use bulk value if set and user presses Enter
    bulk_album = bulk_values.get('album', '')
    current = bulk_album or existing_metadata.get('album', '')
    prompt = f"Album [{current}]" + (" [BULK]" if bulk_album else "")
    new_value = input(f"{prompt}: ").strip()
    new_metadata['album'] = new_value if new_value else current
    
    # Year - use bulk value if set and user presses Enter
    bulk_year = bulk_values.get('year', '')
    current = bulk_year or existing_metadata.get('year', '')
    prompt = f"Year [{current}]" + (" [BULK]" if bulk_year else "")
    new_value = input(f"{prompt}: ").strip()
    new_metadata['year'] = new_value if new_value else current
    
    # Genre - use bulk value if set and user presses Enter
    bulk_genre = bulk_values.get('genre', '')
    current = bulk_genre or existing_metadata.get('genre', '')
    prompt = f"Genre [{current}]" + (" [BULK]" if bulk_genre else "")
    new_value = input(f"{prompt}: ").strip()
    new_metadata['genre'] = new_value if new_value else current
    
    # Track
    current = existing_metadata.get('track', '')
    new_value = input(f"Track # [{current}]: ").strip()
    new_metadata['track'] = new_value if new_value else current
    
    # Cover art
    cover_art_data = bulk_cover_art  # Start with bulk cover art if provided
    has_cover = existing_metadata.get('has_cover', False)
    
    # Determine cover status message
    if bulk_cover_art is not None:
        cover_status = 'Yes [BULK]'
    elif has_cover:
        cover_status = 'Yes'
    else:
        cover_status = 'No'
    
    # Only ask if bulk cover art is not set
    if bulk_cover_art is None:
        response = input(f"\nCurrent cover art: {cover_status}. Add/replace cover art? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            print("\nSelect cover art source:")
            print("  [1] Choose file from disk")
            print("  [2] Skip cover art")
            
            choice = input("Select option: ").strip()
            if choice == '1':
                cover_art_data = select_cover_art_file()
                if cover_art_data:
                    print("✅ Cover art loaded")
                else:
                    print("⚠️  Cover art not loaded")
    else:
        print(f"\n🎨 Using bulk cover art")
    
    return {'metadata': new_metadata, 'cover_art': cover_art_data}


def preview_and_confirm(file_path, old_metadata, new_data):
    """
    Show preview of changes and ask for confirmation.
    Returns True to apply, False to skip.
    """
    print(f"\n{'='*80}")
    print(f"PREVIEW CHANGES: {file_path.name}")
    print(f"{'='*80}")
    
    new_metadata = new_data['metadata']
    
    changes = []
    
    fields = ['title', 'artist', 'album', 'year', 'genre', 'track']
    for field in fields:
        old = old_metadata.get(field, '')
        new = new_metadata.get(field, '')
        
        if old != new:
            changes.append((field.capitalize(), old or '(none)', new or '(none)'))
    
    if new_data.get('cover_art'):
        changes.append(('Cover Art', 'Update', 'Yes'))
    
    if not changes:
        print("\n⚠️  No changes detected")
        return False
    
    print("\nChanges:")
    for field, old, new in changes:
        print(f"  {field:12s}: {old:30s} → {new}")
    
    while True:
        response = input("\nApply these changes? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")


def export_csv(file_list, metadata_list, output_path, label=''):
    """Export metadata to CSV file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Header
            f.write("filename,artist,album,title,track,year,genre,bitrate,duration\n")
            
            # Data
            for file_path, metadata in zip(file_list, metadata_list):
                if metadata is None:
                    continue
                
                filename = file_path.name
                artist = metadata.get('artist', '').replace(',', ';')
                album = metadata.get('album', '').replace(',', ';')
                title = metadata.get('title', '').replace(',', ';')
                track = metadata.get('track', '')
                year = metadata.get('year', '')
                genre = metadata.get('genre', '').replace(',', ';')
                bitrate = metadata.get('bitrate', 0)
                duration = metadata.get('duration', 0)
                
                f.write(f'"{filename}","{artist}","{album}","{title}","{track}","{year}","{genre}",{bitrate},{duration:.2f}\n')
        
        print(f"✅ CSV exported: {output_path} ({label})")
        return True
        
    except Exception as e:
        print(f"❌ CSV export failed: {e}")
        return False


def log_error(log_file, file_path, error_message):
    """Log error to file."""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {file_path.name}: {error_message}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"⚠️  Could not write to log file: {e}")


def main():
    """Main execution function."""
    print("=" * 80)
    print("  MP3 METADATA TAGGER for macOS")
    print("=" * 80)
    
    # Check for mutagen
    if 'mutagen' not in sys.modules:
        print("\n❌ ERROR: Required library 'mutagen' not found")
        sys.exit(1)
    
    # Optional: Setup Discogs
    config = Config()
    if DISCOGS_AVAILABLE and not config.discogs_token:
        config.setup_discogs()
    
    # Select folder
    print("\n📂 Opening folder picker...")
    selected_folder = select_folder_macos()
    
    if not selected_folder:
        print("\n👋 Goodbye!")
        sys.exit(0)
    
    print(f"\n✅ Selected folder: {selected_folder}")
    
    # Find MP3 files
    print("\n🔍 Scanning for MP3 files...")
    mp3_files = find_mp3_files(selected_folder)
    
    if not mp3_files:
        print("\n📭 No MP3 files found in the selected folder.")
        sys.exit(0)
    
    # Display files
    display_file_list(mp3_files, selected_folder)
    
    # Select files to tag
    selected_files = select_files_to_tag(mp3_files)
    
    if not selected_files:
        print("\n⚠️  No files selected")
        sys.exit(0)
    
    # Bulk edit option
    print("\n" + "="*80)
    print("BULK EDITING OPTION")
    print("="*80)
    print("\nDo you want to set common values for all selected files?")
    print("(e.g., same Artist, Album, Year, Genre for the whole album)")
    print("Changes will be applied immediately to all files.")
    
    bulk_values = {}
    response = input("\nEnable bulk editing? (y/n): ").strip().lower()
    if response in ['y', 'yes']:
        bulk_values = bulk_edit_fields(selected_files)
    else:
        print("\n⏭️  Skipping bulk edit (will edit each file individually)")
    
    # Bulk cover art upload
    bulk_cover_mapping = bulk_cover_art_upload(selected_files, selected_folder)
    
    # Check if user wants to continue with individual editing
    has_bulk_changes = bool(bulk_values) or bool(bulk_cover_mapping)
    
    if has_bulk_changes:
        print(f"\n{'='*80}")
        print("BULK EDITING COMPLETE")
        print(f"{'='*80}")
        print("\nYour bulk changes have been applied to the selected files.")
        print("\nOptions:")
        print("  [1] Done - Exit now (bulk changes already saved)")
        print("  [2] Continue to individual file editing (for Track #, Title, etc.)")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            print("\n✅ Bulk editing complete!")
            print(f"\n📁 Logs saved to: {log_dir if 'log_dir' in dir() else Path(selected_folder) / 'mp3_tagger_logs'}")
            
            # Export final metadata before exiting
            log_dir = Path(selected_folder) / 'mp3_tagger_logs'
            log_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            after_csv = log_dir / f'metadata_after_bulk_{timestamp}.csv'
            
            print(f"\n📊 Exporting metadata...")
            after_metadata = [read_mp3_metadata(f) for f in selected_files]
            export_csv(selected_files, after_metadata, after_csv, 'AFTER BULK EDIT')
            
            print(f"\n🎉 All done!")
            print(f"{'='*80}\n")
            sys.exit(0)
    
    # Export BEFORE metadata (for individual editing phase)
    log_dir = Path(selected_folder) / 'mp3_tagger_logs'
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    before_csv = log_dir / f'metadata_before_{timestamp}.csv'
    after_csv = log_dir / f'metadata_after_{timestamp}.csv'
    error_log = log_dir / f'errors_{timestamp}.log'
    
    print(f"\n📊 Reading metadata for CSV export...")
    before_metadata = [read_mp3_metadata(f) for f in selected_files]
    export_csv(selected_files, before_metadata, before_csv, 'BEFORE')
    
    # Process each file
    print(f"\n{'='*80}")
    print("STARTING TAGGING PROCESS")
    print(f"{'='*80}")
    
    successful = 0
    skipped = 0
    failed = 0
    
    for idx, file_path in enumerate(selected_files, 1):
        print(f"\n\n{'='*80}")
        print(f"FILE {idx}/{len(selected_files)}")
        print(f"{'='*80}")
        
        # Read existing metadata
        existing_metadata = read_mp3_metadata(file_path)
        
        if existing_metadata is None:
            print(f"❌ Could not read file: {file_path.name}")
            log_error(error_log, file_path, "Could not read MP3 file")
            failed += 1
            continue
        
        # Get bulk cover art for this file (if applicable)
        file_bulk_cover = bulk_cover_mapping.get(str(file_path))
        
        # Interactive editing
        new_data = edit_metadata_interactive(file_path, existing_metadata, bulk_values, file_bulk_cover)
        
        if new_data is None:
            print(f"⏭️  Skipped: {file_path.name}")
            skipped += 1
            continue
        
        # Preview and confirm
        if not preview_and_confirm(file_path, existing_metadata, new_data):
            print(f"⏭️  Skipped: {file_path.name}")
            skipped += 1
            continue
        
        # Apply changes
        print("\n💾 Saving changes...")
        success, error = write_mp3_metadata(
            file_path,
            new_data['metadata'],
            new_data.get('cover_art')
        )
        
        if success:
            print(f"✅ SUCCESS: {file_path.name}")
            successful += 1
        else:
            print(f"❌ FAILED: {file_path.name}")
            print(f"   Error: {error}")
            log_error(error_log, file_path, error)
            failed += 1
    
    # Export AFTER metadata
    print(f"\n📊 Exporting final metadata...")
    after_metadata = [read_mp3_metadata(f) for f in selected_files]
    export_csv(selected_files, after_metadata, after_csv, 'AFTER')
    
    # Final summary
    print(f"\n{'='*80}")
    print("📈 FINAL RESULTS")
    print(f"{'='*80}")
    print(f"Total files processed: {len(selected_files)}")
    print(f"✅ Successfully tagged: {successful}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Failed: {failed}")
    
    print(f"\n📁 Logs saved to: {log_dir}")
    print(f"   - {before_csv.name}")
    print(f"   - {after_csv.name}")
    if failed > 0:
        print(f"   - {error_log.name}")
    
    print(f"\n🎉 Tagging complete!")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
