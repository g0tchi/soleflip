#!/usr/bin/env python3
"""
Demo script for the Retro CLI without requiring database connections
"""

import time

from utils import clear_screen, colored_text, keygen_animation, show_banner, wait_for_key


def demo_startup():
    """Demo startup sequence"""
    clear_screen()
    show_banner()
    time.sleep(1)

    print(colored_text("═" * 60, "cyan"))
    print(colored_text("  INITIALIZING DEMO MODE...", "green"))
    print(colored_text("═" * 60, "cyan"))

    time.sleep(1)


def demo_authentication():
    """Demo authentication"""
    print(colored_text("\n" + "─" * 40, "yellow"))
    print(colored_text("  DEMO AUTHENTICATION", "red"))
    print(colored_text("─" * 40, "yellow"))

    username = input(colored_text("\nEnter demo codename: ", "cyan")).strip()
    if not username:
        username = "demo_user"

    keygen_animation(f"Generating demo key for {username}")

    print(colored_text("\n✓ DEMO ACCESS GRANTED", "green"))
    print(colored_text(f"  User: {username}", "yellow"))
    print(colored_text("  Mode: DEMONSTRATION", "yellow"))

    return username


def demo_menu(username):
    """Demo menu system"""
    while True:
        clear_screen()
        print(colored_text("═" * 50, "cyan"))
        print(colored_text("  RETRO CLI DEMONSTRATION", "yellow"))
        print(colored_text("═" * 50, "cyan"))

        menu_options = [
            ("1", "Show ASCII Art Demo", "green"),
            ("2", "Color System Demo", "blue"),
            ("3", "Animation Demo", "magenta"),
            ("4", "Configuration Demo", "yellow"),
            ("5", "Security Demo", "cyan"),
            ("Q", "Quit Demo", "red"),
        ]

        for key, desc, color in menu_options:
            print(colored_text(f"  [{key}] {desc}", color))

        print(colored_text("═" * 50, "cyan"))

        choice = input(colored_text(f"\n{username}@retro-demo> ", "cyan")).upper()

        if choice == "Q":
            print(colored_text("\n✓ Demo ending...", "yellow"))
            keygen_animation("Cleaning up demo session")
            print(colored_text(f"Goodbye, {username}!", "green"))
            break
        elif choice == "1":
            demo_ascii_art()
        elif choice == "2":
            demo_colors()
        elif choice == "3":
            demo_animations()
        elif choice == "4":
            demo_configuration()
        elif choice == "5":
            demo_security()
        else:
            print(colored_text("Invalid command! Try again.", "red"))
            time.sleep(1)


def demo_ascii_art():
    """Demonstrate ASCII art capabilities"""
    clear_screen()
    print(colored_text("ASCII ART DEMONSTRATION", "bright_cyan"))
    print(colored_text("═" * 40, "cyan"))

    # Show different banner sizes
    print(colored_text("\nResponsive ASCII Banner:", "bright_white"))
    show_banner()

    wait_for_key()


def demo_colors():
    """Demonstrate color system"""
    clear_screen()
    print(colored_text("COLOR SYSTEM DEMO", "bright_cyan"))
    print(colored_text("═" * 30, "cyan"))

    colors = [
        ("red", "Error messages"),
        ("green", "Success messages"),
        ("yellow", "Warning messages"),
        ("blue", "Information"),
        ("magenta", "Special features"),
        ("cyan", "Highlights"),
        ("bright_red", "Critical errors"),
        ("bright_green", "Major success"),
        ("bright_yellow", "Important warnings"),
        ("bright_blue", "Key information"),
        ("bright_magenta", "Premium features"),
        ("bright_cyan", "System messages"),
    ]

    print(colored_text("\nColor Palette:", "bright_white"))
    for color, description in colors:
        print(colored_text(f"  {color:15} - {description}", color))

    wait_for_key()


def demo_animations():
    """Demonstrate animation capabilities"""
    clear_screen()
    print(colored_text("ANIMATION DEMO", "bright_cyan"))
    print(colored_text("═" * 25, "cyan"))

    # Keygen animation
    keygen_animation("Demo key generation")

    # Loading animation (simulated)
    print(colored_text("\nProgress bar demo:", "bright_white"))
    from utils import progress_bar

    progress_bar("Loading demo data", 50, 0.05)

    print(colored_text("\nAnimation demo complete!", "bright_green"))
    wait_for_key()


def demo_configuration():
    """Demonstrate configuration system"""
    clear_screen()
    print(colored_text("CONFIGURATION DEMO", "bright_cyan"))
    print(colored_text("═" * 30, "cyan"))

    try:
        from config import get_config

        config = get_config()

        print(colored_text("\nConfiguration Status:", "bright_white"))
        validation = config.validate()

        for service, status in validation.items():
            status_text = "CONFIGURED" if status else "MISSING"
            color = "bright_green" if status else "red"
            print(colored_text(f"  {service:15} - {status_text}", color))

        print(colored_text(f"\nEnvironment: {config.system.environment}", "cyan"))
        print(colored_text(f"Debug Mode: {config.system.debug}", "cyan"))
        print(colored_text(f"Test Mode: {config.system.is_test}", "cyan"))

    except Exception as e:
        print(colored_text(f"Configuration error: {e}", "red"))

    wait_for_key()


def demo_security():
    """Demonstrate security features"""
    clear_screen()
    print(colored_text("SECURITY DEMO", "bright_cyan"))
    print(colored_text("═" * 25, "cyan"))

    try:
        from security import SecurityManager

        from config import get_config

        config = get_config()
        security_manager = SecurityManager(config)

        print(colored_text("\nSecurity Features:", "bright_white"))

        # Start demo session
        session_id = security_manager.start_session("demo_user")
        print(colored_text(f"Session started: {session_id}", "green"))

        # Log some activities
        security_manager.update_session_activity("demo_menu_access")
        security_manager.update_session_activity("security_demo")

        # Show session stats
        stats = security_manager.get_session_stats()
        print(colored_text(f"Actions logged: {stats['actions_performed']}", "green"))

        # Security check
        security_status = security_manager.check_system_security()
        env_secure = security_status["environment_secure"]
        print(colored_text(f"Environment secure: {env_secure}", "green" if env_secure else "red"))

        # End session
        security_manager.end_session()
        print(colored_text("Session ended and logged", "green"))

    except Exception as e:
        print(colored_text(f"Security demo error: {e}", "red"))

    wait_for_key()


if __name__ == "__main__":
    try:
        print(colored_text("Starting Retro CLI Demo...", "bright_magenta"))
        time.sleep(1)

        demo_startup()
        username = demo_authentication()
        demo_menu(username)

        print(colored_text("\nThank you for trying the Retro CLI Demo!", "bright_magenta"))

    except KeyboardInterrupt:
        print(colored_text("\nDemo interrupted by user", "yellow"))
    except Exception as e:
        print(colored_text(f"\nDemo error: {e}", "red"))
    finally:
        print(colored_text("Demo session ended.", "dim"))
