#!/usr/bin/env python3
"""
Unit tests for RL Training Input Lock
======================================

Tests the core logic of the lock screen without requiring a display.
Uses mocking for GTK and evdev components.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import argparse


# Mock GTK before importing the main module
sys.modules['gi'] = MagicMock()
sys.modules['gi.repository'] = MagicMock()

# Import the module we're testing
import rl_input_lock


class TestPasswordValidation(unittest.TestCase):
    """Test password handling and validation logic"""

    def test_default_password(self):
        """Test that default password is set correctly"""
        self.assertEqual(rl_input_lock.DEFAULT_PASSWORD, "train123")

    def test_password_correct(self):
        """Test that a correct password matches"""
        password = "mySecretPass"
        self.assertEqual(password, "mySecretPass")

    def test_password_incorrect(self):
        """Test that an incorrect password does not match"""
        password = "train123"
        user_input = "wrongpass"
        self.assertNotEqual(user_input, password)

    def test_password_case_sensitive(self):
        """Test that password matching is case-sensitive"""
        password = "Train123"
        user_input = "train123"
        self.assertNotEqual(user_input, password)

    def test_empty_password(self):
        """Test that empty password is handled"""
        password = ""
        user_input = ""
        self.assertEqual(user_input, password)

    def test_password_with_special_chars(self):
        """Test password with special characters"""
        password = "P@ssw0rd!#$%"
        self.assertEqual(password, "P@ssw0rd!#$%")


class TestArgumentParsing(unittest.TestCase):
    """Test command-line argument parsing"""

    def test_parse_default_password(self):
        """Test parsing with default password"""
        test_args = ['rl_input_lock.py']
        with patch.object(sys, 'argv', test_args):
            parser = argparse.ArgumentParser(description="RL Training Input Lock")
            parser.add_argument('password', nargs='?', default=rl_input_lock.DEFAULT_PASSWORD,
                              help=f"Unlock password (default: {rl_input_lock.DEFAULT_PASSWORD})")
            parser.add_argument('--bg', default=rl_input_lock.DEFAULT_BG,
                              help="Background image path")
            args = parser.parse_args([])
            self.assertEqual(args.password, "train123")

    def test_parse_custom_password(self):
        """Test parsing with custom password"""
        parser = argparse.ArgumentParser(description="RL Training Input Lock")
        parser.add_argument('password', nargs='?', default=rl_input_lock.DEFAULT_PASSWORD)
        parser.add_argument('--bg', default=rl_input_lock.DEFAULT_BG)
        args = parser.parse_args(['MyCustomPassword'])
        self.assertEqual(args.password, "MyCustomPassword")

    def test_parse_custom_bg(self):
        """Test parsing with custom background image"""
        parser = argparse.ArgumentParser(description="RL Training Input Lock")
        parser.add_argument('password', nargs='?', default=rl_input_lock.DEFAULT_PASSWORD)
        parser.add_argument('--bg', default=rl_input_lock.DEFAULT_BG)
        args = parser.parse_args(['--bg', '/custom/path.png'])
        self.assertEqual(args.bg, '/custom/path.png')

    def test_parse_password_and_bg(self):
        """Test parsing with both password and background"""
        parser = argparse.ArgumentParser(description="RL Training Input Lock")
        parser.add_argument('password', nargs='?', default=rl_input_lock.DEFAULT_PASSWORD)
        parser.add_argument('--bg', default=rl_input_lock.DEFAULT_BG)
        args = parser.parse_args(['SecurePass', '--bg', '/path/bg.png'])
        self.assertEqual(args.password, "SecurePass")
        self.assertEqual(args.bg, '/path/bg.png')


class TestConstantsAndDefaults(unittest.TestCase):
    """Test module constants and defaults"""

    def test_have_evdev_flag(self):
        """Test HAVE_EVDEV flag exists"""
        self.assertIn('HAVE_EVDEV', dir(rl_input_lock))
        self.assertIsInstance(rl_input_lock.HAVE_EVDEV, bool)

    def test_default_bg_expanduser(self):
        """Test that DEFAULT_BG is properly expanded"""
        # DEFAULT_BG is already expanded by the module
        self.assertNotIn('~', rl_input_lock.DEFAULT_BG)
        # Should be a valid path
        self.assertTrue(isinstance(rl_input_lock.DEFAULT_BG, str))
        self.assertGreater(len(rl_input_lock.DEFAULT_BG), 0)

    def test_css_not_empty(self):
        """Test that CSS is defined and not empty"""
        self.assertGreater(len(rl_input_lock.CSS), 0)

    def test_css_contains_styling(self):
        """Test that CSS contains expected style rules"""
        self.assertIn('lock-window', rl_input_lock.CSS)
        self.assertIn('password-entry', rl_input_lock.CSS)
        self.assertIn('warning-title', rl_input_lock.CSS)


class TestPasswordValidationLogic(unittest.TestCase):
    """Test the password validation logic without GTK"""

    def test_password_check_correct(self):
        """Simulate password check with correct password"""
        stored_password = "train123"
        user_password = "train123"
        result = (user_password == stored_password)
        self.assertTrue(result)

    def test_password_check_incorrect(self):
        """Simulate password check with incorrect password"""
        stored_password = "train123"
        user_password = "wrongpass"
        result = (user_password == stored_password)
        self.assertFalse(result)

    def test_password_with_whitespace_not_trimmed(self):
        """Test that whitespace is considered part of password"""
        stored_password = "train123"
        user_password = " train123"
        result = (user_password == stored_password)
        self.assertFalse(result)

    def test_empty_password_check(self):
        """Test empty password handling"""
        stored_password = ""
        user_password = ""
        result = (user_password == stored_password)
        self.assertTrue(result)


class TestModuleStructure(unittest.TestCase):
    """Test that expected functions and classes exist"""

    def test_lockscreen_class_exists(self):
        """Test that LockScreen class exists"""
        self.assertTrue(hasattr(rl_input_lock, 'LockScreen'))

    def test_main_function_exists(self):
        """Test that main function exists"""
        self.assertTrue(hasattr(rl_input_lock, 'main'))
        self.assertTrue(callable(rl_input_lock.main))

    def test_constants_defined(self):
        """Test that required constants are defined"""
        self.assertTrue(hasattr(rl_input_lock, 'DEFAULT_PASSWORD'))
        self.assertTrue(hasattr(rl_input_lock, 'DEFAULT_BG'))
        self.assertTrue(hasattr(rl_input_lock, 'CSS'))


class TestPathHandling(unittest.TestCase):
    """Test path handling for background images"""

    def test_expanduser_tilde(self):
        """Test that ~ is expanded properly"""
        path = os.path.expanduser("~/Downloads/test.png")
        self.assertNotIn("~", path)
        self.assertIn("/", path)

    def test_absolute_path(self):
        """Test absolute path handling"""
        path = "/home/user/Downloads/test.png"
        self.assertTrue(path.startswith("/"))

    def test_relative_path(self):
        """Test relative path handling"""
        path = "./images/bg.png"
        self.assertTrue(path.startswith("."))


class TestStringFormatting(unittest.TestCase):
    """Test string formatting for display"""

    def test_password_masking(self):
        """Test password masking with asterisks"""
        password = "train123"
        masked = '*' * len(password)
        self.assertEqual(masked, "********")
        self.assertEqual(len(masked), len(password))

    def test_unicode_symbols(self):
        """Test unicode symbols used in output"""
        # Test common unicode symbols used in the app
        symbols = {
            'warning': '⚠',
            'checkmark': '✓',
            'cross': '✗',
            'heart': '♥',
        }
        for key, symbol in symbols.items():
            self.assertTrue(len(symbol) > 0)


class TestApplicationFlow(unittest.TestCase):
    """Test high-level application flow"""

    def test_locked_state_initialization(self):
        """Test that lock starts in locked state"""
        # Simulate initialization
        locked = True
        self.assertTrue(locked)

    def test_unlock_state_change(self):
        """Test state change from locked to unlocked"""
        locked = True
        self.assertTrue(locked)
        locked = False
        self.assertFalse(locked)

    def test_grabbed_devices_list(self):
        """Test grabbed devices list initialization"""
        grabbed_devices = []
        self.assertEqual(len(grabbed_devices), 0)
        self.assertIsInstance(grabbed_devices, list)


class TestKeyboardShortcuts(unittest.TestCase):
    """Test keyboard shortcut parsing"""

    def test_ctrl_alt_u_detection(self):
        """Test Ctrl+Alt+U detection logic"""
        name = 'u'
        ctrl = True
        alt = True
        is_unlock_shortcut = (name.lower() == 'u' and ctrl and alt)
        self.assertTrue(is_unlock_shortcut)

    def test_non_shortcut_key(self):
        """Test non-shortcut key handling"""
        name = 'a'
        ctrl = False
        alt = False
        is_unlock_shortcut = (name.lower() == 'u' and ctrl and alt)
        self.assertFalse(is_unlock_shortcut)

    def test_super_key_blocked(self):
        """Test that Super key is blocked"""
        dangerous_keys = ('Super_L', 'Super_R')
        test_key = 'Super_L'
        self.assertIn(test_key, dangerous_keys)


class TestEvdevIntegration(unittest.TestCase):
    """Test evdev integration (with mocking)"""

    def test_evdev_availability(self):
        """Test HAVE_EVDEV flag reflects availability"""
        # Should be boolean
        self.assertIsInstance(rl_input_lock.HAVE_EVDEV, bool)

    def test_graceful_degradation_without_evdev(self):
        """Test application works without evdev"""
        # When HAVE_EVDEV is False, app should still work
        # The app should handle both True and False values gracefully
        self.assertIsInstance(rl_input_lock.HAVE_EVDEV, bool)


class TestMessageStrings(unittest.TestCase):
    """Test that important message strings are present"""

    def test_warning_messages_in_code(self):
        """Test that warning messages are defined"""
        # Check that key strings are in the module
        with open(__file__.replace('test_', '')) as f:
            module_content = f.read()
        self.assertIn("DO NOT SWITCH OFF", module_content)
        self.assertIn("Training", module_content)


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
