#!/usr/bin/env python3
"""
Retro Keygen Utils - ASCII Art, Animations, and Visual Effects
"""

import time
import random
import os
import sys
from typing import List

# ANSI Color Codes for cross-platform support
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Standard colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

def colored_text(text: str, color: str) -> str:
    """Apply color to text using ANSI codes"""
    color_map = {
        "red": Colors.RED,
        "green": Colors.GREEN,
        "yellow": Colors.YELLOW,
        "blue": Colors.BLUE,
        "magenta": Colors.MAGENTA,
        "cyan": Colors.CYAN,
        "white": Colors.WHITE,
        "bright_red": Colors.BRIGHT_RED,
        "bright_green": Colors.BRIGHT_GREEN,
        "bright_yellow": Colors.BRIGHT_YELLOW,
        "bright_blue": Colors.BRIGHT_BLUE,
        "bright_magenta": Colors.BRIGHT_MAGENTA,
        "bright_cyan": Colors.BRIGHT_CYAN,
        "bright_white": Colors.BRIGHT_WHITE,
        "reset": Colors.RESET,
        "dim": Colors.DIM,
        # Claude Code theme colors - Updated for better contrast
        "purple": '\033[95m',               # Bright Magenta for main theme
        "violet": '\033[35m',               # Regular Magenta for secondary
        "success": Colors.BRIGHT_GREEN,     # Success green
        "info": Colors.BRIGHT_CYAN,         # Info cyan
        "warning": Colors.BRIGHT_YELLOW,    # Warning yellow
        "error": Colors.BRIGHT_RED,         # Error red
        "muted": Colors.BRIGHT_BLACK,       # Muted gray
        "accent": Colors.BRIGHT_BLUE        # Accent blue
    }
    
    color_code = color_map.get(color.lower(), Colors.WHITE)
    return f"{color_code}{text}{Colors.RESET}"

def status_icon(status: str) -> str:
    """Get a status icon with appropriate coloring (Claude Code theme - ASCII safe)"""
    icons = {
        "success": colored_text("[+]", "success"),
        "ok": colored_text("[+]", "success"),  
        "connected": colored_text("[+]", "success"),
        "ready": colored_text("[+]", "success"),
        "processing": colored_text("[~]", "purple"),
        "error": colored_text("[!]", "error"),
        "failed": colored_text("[!]", "error"),
        "missing": colored_text("[?]", "warning"),
        "warning": colored_text("[!]", "warning"),
        "info": colored_text("[i]", "info"),
        "loading": colored_text("[.]", "violet"),
        "pending": colored_text("[ ]", "muted")
    }
    return icons.get(status.lower(), colored_text("[?]", "muted"))

def format_status_line(label: str, status: str, details: str = "") -> str:
    """Format a status line with icon, label and details"""
    icon = status_icon(status)
    main_text = colored_text(f" {label}", "purple")
    detail_text = colored_text(f" {details}", "muted") if details else ""
    return f"{icon}{main_text}{detail_text}"

def section_header(title: str, color: str = "purple") -> str:
    """Create a section header with consistent styling"""
    return colored_text(f"\n> {title}", color)

def get_terminal_width() -> int:
    """Get terminal width safely"""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80  # fallback

def show_banner():
    """Display retro keygen style banner"""
    clear_screen()
    
    terminal_width = get_terminal_width()
    
    # ASCII Art - responsive design
    if terminal_width >= 100:
        banner = """
+==========================================================================================+
|                                                                                          |
|  SSSSSSS  OOOOO  LL      EEEEEEE FFFFFF LL    III PPPPPP  PPPPPP  EEEEEEE RRRRR        |
|  SS      OO   OO LL      EE      FF     LL     I  PP   PP PP   PP EE      RR   R       |
|  SSSSSSS OO   OO LL      EEEEE   FFFFF  LL     I  PPPPPP  PPPPPP  EEEEE   RRRRR        |
|       SS OO   OO LL      EE      FF     LL     I  PP      PP      EE      RR  R        |
|  SSSSSSS  OOOOO  LLLLLLL EEEEEEE FF     LLLLL III PP      PP      EEEEEEE RR   R       |
|                                                                                          |
|                 * CLAUDE CODE INSPIRED ADMIN PANEL *                                  |
|                                      v1.0.0 - 2025 Edition                             |
|                                                                                          |
+==========================================================================================+
"""
    elif terminal_width >= 80:
        banner = """
+=========================================================================+
|                                                                         |
|  #######  ######  #      ####### ####### #      ## ###### ######      |
|  ##       ##   ## #      ##      ##      #      ## ##   ## ##   ##     |
|  #######  ##   ## #      #####   #####   #      ## ###### ######      |
|       ##  ##   ## #      ##      ##      #      ## ##     ##           |
|  #######  ######  ###### ####### ##      ###### ## ##     ##           |
|                                                                         |
|                 * CLAUDE CODE INSPIRED ADMIN PANEL *                   |
|                           v1.0.0 - 2025 Edition                        |
|                                                                         |
+=========================================================================+
"""
    else:
        banner = """
+------------------------------------+
|                                    |
|    SSSSS  OOOOO  LL      EEEEE    |
|    SS     OO   O LL      EE       |
|    SSSSS  OO   O LL      EEEEE    |
|        SS OO   O LL      EE       |
|    SSSSS   OOOO  LLLLLLL EEEEE    |
|                                    |
|      RETRO ADMIN CLI               |
|         v1.0.0 - 2025              |
|                                    |
+------------------------------------+
"""
    
    # Print banner with Claude Code colors
    lines = banner.strip().split('\n')
    for i, line in enumerate(lines):
        if 'SOLEFLIPPER' in line or 'CLAUDE CODE' in line:
            print(colored_text(line, "purple"))
        elif 'ADMIN PANEL' in line or 'v1.0.0' in line:
            print(colored_text(line, "violet"))
        else:
            print(colored_text(line, "success"))

def keygen_animation(message: str):
    """Keygen style loading animation with fake key generation"""
    print(colored_text(f"\n[*] {message}...", "bright_cyan"))
    
    # Loading animation
    chars = "/-\\|"
    for i in range(30):
        char = chars[i % len(chars)]
        print(colored_text(f"\r  {char} Processing...", "yellow"), end="", flush=True)
        time.sleep(0.1)
    
    print(colored_text("\r  [OK] Complete!        ", "bright_green"))
    
    # Fake progress with random data
    progress_steps = [
        "Initializing crypto module",
        "Generating entropy pool",
        "Creating RSA key pair", 
        "Encoding certificate",
        "Finalizing key generation"
    ]
    
    for step in progress_steps:
        print(colored_text(f"  * {step}...", "cyan"), end="", flush=True)
        time.sleep(random.uniform(0.3, 0.8))
        print(colored_text(" [OK]", "bright_green"))

def progress_bar(description: str, total: int, delay: float = 0.05):
    """Display progress bar with retro styling"""
    print(colored_text(f"\n{description}:", "bright_cyan"))
    
    bar_width = min(50, get_terminal_width() - 20)
    
    for i in range(total + 1):
        percent = int((i / total) * 100)
        filled_width = int((i / total) * bar_width)
        
        bar = "#" * filled_width + "." * (bar_width - filled_width)
        
        print(colored_text(f"\r[{bar}] {percent:3d}% ", "bright_magenta"), end="", flush=True)
        time.sleep(delay)
    
    print(colored_text(" [OK] Complete!", "bright_green"))

def matrix_effect(duration: int = 3):
    """Matrix-style scrolling effect"""
    try:
        terminal_width = get_terminal_width()
        chars = "01ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        start_time = time.time()
        while time.time() - start_time < duration:
            line = ''.join(random.choice(chars) for _ in range(terminal_width - 1))
            print(colored_text(line, "bright_green"))
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        pass

def typewriter_effect(text: str, delay: float = 0.05):
    """Typewriter effect for dramatic text display"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()  # newline at end

def glitch_text(text: str, glitch_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?") -> str:
    """Apply glitch effect to text"""
    result = list(text)
    num_glitches = random.randint(1, min(3, len(text) // 3))
    
    for _ in range(num_glitches):
        pos = random.randint(0, len(result) - 1)
        result[pos] = random.choice(glitch_chars)
    
    return ''.join(result)

def generate_fake_key() -> str:
    """Generate fake license key"""
    segments = []
    for _ in range(4):
        segment = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=4))
        segments.append(segment)
    return '-'.join(segments)

def draw_box(text: str, padding: int = 2) -> str:
    """Draw a box around text"""
    lines = text.split('\n')
    max_length = max(len(line) for line in lines)
    
    # Calculate box dimensions
    box_width = max_length + (padding * 2)
    
    # Create box
    top = '╔' + '═' * box_width + '╗'
    bottom = '╚' + '═' * box_width + '╝'
    
    result = [top]
    
    # Add padding lines
    for _ in range(padding):
        result.append('║' + ' ' * box_width + '║')
    
    # Add content lines
    for line in lines:
        padding_left = ' ' * padding
        padding_right = ' ' * (box_width - len(line) - padding)
        result.append('║' + padding_left + line + padding_right + '║')
    
    # Add padding lines
    for _ in range(padding):
        result.append('║' + ' ' * box_width + '║')
    
    result.append(bottom)
    
    return '\n'.join(result)

def retro_menu_frame(options: List[str], selected: int = 0) -> str:
    """Create retro-style menu frame"""
    menu_items = []
    
    for i, option in enumerate(options):
        if i == selected:
            # Highlighted option
            menu_items.append(f"► {option}")
        else:
            menu_items.append(f"  {option}")
    
    return '\n'.join(menu_items)

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def wait_for_key():
    """Wait for user to press any key"""
    if os.name == 'nt':
        # Windows
        import msvcrt
        print(colored_text("\nPress any key to continue...", "dim"))
        msvcrt.getch()
    else:
        # Unix/Linux/Mac
        input(colored_text("\nPress Enter to continue...", "dim"))

def retro_loading_dots(message: str, duration: int = 3):
    """Loading animation with dots"""
    print(colored_text(f"{message}", "bright_cyan"), end="", flush=True)
    
    for i in range(duration * 4):
        dots = "." * ((i % 4) + 1)
        padding = " " * (4 - len(dots))
        print(f"\r{colored_text(message + dots + padding, 'bright_cyan')}", end="", flush=True)
        time.sleep(0.25)
    
    print(colored_text(f"\r{message}... ✓ Done!", "bright_green"))

def random_hex_string(length: int = 32) -> str:
    """Generate random hex string for fake keys/tokens"""
    return ''.join(random.choices('0123456789ABCDEF', k=length))

def security_scan_animation():
    """Fake security scan animation"""
    scan_items = [
        "Registry integrity",
        "System files", 
        "Network connections",
        "Process validation",
        "Memory protection",
        "Crypto modules"
    ]
    
    print(colored_text("\n🔐 SECURITY SCAN IN PROGRESS", "bright_yellow"))
    print(colored_text("═" * 40, "yellow"))
    
    for item in scan_items:
        print(colored_text(f"Scanning {item}...", "cyan"), end="", flush=True)
        time.sleep(random.uniform(0.5, 1.2))
        print(colored_text(" ✓ OK", "bright_green"))
    
    print(colored_text("\n🛡️  SYSTEM SECURE - NO THREATS DETECTED", "bright_green"))

def get_system_info() -> dict:
    """Get fake system information for display"""
    return {
        "os": f"Windows {random.randint(10, 11)}",
        "architecture": random.choice(["x64", "x86"]),
        "processor": f"Intel Core i{random.randint(3, 9)}",
        "memory": f"{random.randint(8, 32)}GB RAM",
        "graphics": random.choice(["NVIDIA RTX", "AMD Radeon", "Intel UHD"]),
        "network": random.choice(["Ethernet", "WiFi", "Cellular"]),
        "uptime": f"{random.randint(1, 23)}:{random.randint(10, 59)}:{random.randint(10, 59)}"
    }

if __name__ == "__main__":
    # Demo of utility functions
    show_banner()
    time.sleep(2)
    
    keygen_animation("Generating access credentials")
    
    progress_bar("Loading system modules", 100, 0.02)
    
    print(colored_text("\n" + draw_box("SYSTEM READY\nAccess Granted"), "bright_green"))
    
    wait_for_key()