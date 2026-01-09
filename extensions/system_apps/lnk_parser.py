# extensions/system_apps/lnk_parser.py
import struct
from typing import Optional

def resolve_lnk(path: str) -> Optional[str]:
    """
    Parse a Windows .lnk shortcut file and return the target path.
    Pure Python - no dependencies.
    """
    try:
        with open(path, 'rb') as f:
            data = f.read()
        
        # Header is 76 bytes
        if len(data) < 76:
            return None
        
        # Verify magic number (CLSID)
        # 4C 00 00 00 = 0x0000004C
        if data[0:4] != b'\x4c\x00\x00\x00':
            return None
        
        # Link flags at offset 0x14 (20)
        flags = struct.unpack('<I', data[0x14:0x18])[0]
        
        has_link_target_id_list = flags & 0x01
        has_link_info = flags & 0x02
        
        offset = 76  # Start after header
        
        # Skip LinkTargetIDList if present
        if has_link_target_id_list:
            if offset + 2 > len(data):
                return None
            id_list_size = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2 + id_list_size
        
        # Parse LinkInfo if present
        if has_link_info:
            if offset + 4 > len(data):
                return None
            
            link_info_size = struct.unpack('<I', data[offset:offset+4])[0]
            link_info_start = offset
            
            if offset + 28 > len(data):
                return None
            
            # LinkInfo header
            link_info_header_size = struct.unpack('<I', data[offset+4:offset+8])[0]
            link_info_flags = struct.unpack('<I', data[offset+8:offset+12])[0]
            
            # Volume ID offset and Local Base Path offset
            local_base_path_offset = struct.unpack('<I', data[offset+16:offset+20])[0]
            
            # Check for Unicode path (header size > 28 means we have extra fields)
            local_base_path_offset_unicode = 0
            if link_info_header_size >= 0x24:
                if offset + 0x24 > len(data):
                    return None
                local_base_path_offset_unicode = struct.unpack('<I', data[offset+0x20:offset+0x24])[0]
            
            # VolumeIDAndLocalBasePath flag
            if link_info_flags & 0x01:
                # Try Unicode path first
                if local_base_path_offset_unicode:
                    path_start = link_info_start + local_base_path_offset_unicode
                    target = _read_unicode_string(data, path_start)
                    if target:
                        return target
                
                # Fall back to ANSI path
                if local_base_path_offset:
                    path_start = link_info_start + local_base_path_offset
                    target = _read_ansi_string(data, path_start)
                    if target:
                        return target
            
            offset += link_info_size
        
        # Try StringData section for relative path or working dir
        # This is a fallback if LinkInfo didn't work
        has_name = flags & 0x04
        has_relative_path = flags & 0x08
        has_working_dir = flags & 0x10
        
        # Skip name string
        if has_name:
            offset = _skip_string_data(data, offset, flags)
        
        # Get relative path
        if has_relative_path and offset < len(data):
            rel_path = _read_string_data(data, offset, flags)
            if rel_path:
                return rel_path
        
        return None
        
    except Exception:
        return None


def _read_ansi_string(data: bytes, offset: int) -> Optional[str]:
    """Read null-terminated ANSI string."""
    try:
        end = data.index(b'\x00', offset)
        return data[offset:end].decode('cp1252', errors='ignore')
    except (ValueError, UnicodeDecodeError):
        return None


def _read_unicode_string(data: bytes, offset: int) -> Optional[str]:
    """Read null-terminated UTF-16LE string."""
    try:
        result = []
        while offset + 1 < len(data):
            char = struct.unpack('<H', data[offset:offset+2])[0]
            if char == 0:
                break
            result.append(chr(char))
            offset += 2
        return ''.join(result) if result else None
    except Exception:
        return None


def _skip_string_data(data: bytes, offset: int, flags: int) -> int:
    """Skip a StringData entry and return new offset."""
    if offset + 2 > len(data):
        return offset
    count = struct.unpack('<H', data[offset:offset+2])[0]
    is_unicode = flags & 0x80  # IsUnicode flag
    char_size = 2 if is_unicode else 1
    return offset + 2 + (count * char_size)


def _read_string_data(data: bytes, offset: int, flags: int) -> Optional[str]:
    """Read a StringData entry."""
    if offset + 2 > len(data):
        return None
    count = struct.unpack('<H', data[offset:offset+2])[0]
    is_unicode = flags & 0x80
    
    if is_unicode:
        string_data = data[offset+2:offset+2+(count*2)]
        return string_data.decode('utf-16-le', errors='ignore')
    else:
        string_data = data[offset+2:offset+2+count]
        return string_data.decode('cp1252', errors='ignore')