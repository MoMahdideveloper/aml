"""
Device detection utility for Flask template selection.
Provides mobile/device detection based on User-Agent parsing.
"""

import re
from typing import Optional


class DeviceDetector:
    """Detects device type from User-Agent string."""

    def __init__(self):
        """Initialize device detector with compiled regex patterns."""
        # Mobile device patterns
        self.mobile_patterns = [
            r'iphone', r'ipod', r'android.*mobile', r'windows.*phone',
            r'blackberry', r'opd', r'opera mini', r'iemobile',
            r'fennec', r'minimo', r'netfront', r'blazer',
            r'iemobile', r'midp', r'wap', r'up.browser',
            r'up.link', r'audio', r'au-mic', r'\+vodafone\/',
            r'-wap', r'kindle', r'nokia', r'htc', r'_mobile',
            r'mobile', r'pda', r'palm', r'smartphone',
            r'wap-browser', r'vodafone', r'up\.browser',
            r'up\.link', r'windows ce', r'pocket',
            r'psp', r'nintendo dsi'
        ]

        # Tablet patterns
        self.tablet_patterns = [
            r'ipad', r'playbook', r'silk', r'android(?!.*mobile)',
            r'kindle fire', r'xoom', r'sch-i800',
            r'tablet', r'nexus 7', r'nexus 10',
            r'gt-p1000', r'gt-p1003', r'gt-p7500',
            r'gt-n7000', r'sgh-t849', r'sgh-t859',
            r'sgh-t959', r'sgh-t959v', r'kindle',
            r'nook', r'docomo', r'infonexus',
            r' tablet ', r'gtp1000', r'gtp1003',
            r'sharp tab q'
        ]

        # Compile patterns for efficiency
        self.mobile_regex = re.compile('|'.join(self.mobile_patterns), re.I)
        self.tablet_regex = re.compile('|'.join(self.tablet_patterns), re.I)

    def is_mobile(self, user_agent: Optional[str] = None) -> bool:
        """
        Detect if the request is from a mobile device.

        Args:
            user_agent: User-Agent string (if None, will attempt to get from request)

        Returns:
            True if mobile device, False otherwise
        """
        if not user_agent:
            return False

        user_agent = user_agent.lower()

        # Check for tablet exceptions (some tablets might match mobile patterns)
        if self.tablet_regex.search(user_agent):
            return False

        # Check for mobile patterns
        return bool(self.mobile_regex.search(user_agent))

    def is_tablet(self, user_agent: Optional[str] = None) -> bool:
        """
        Detect if the request is from a tablet device.

        Args:
            user_agent: User-Agent string (if None, will attempt to get from request)

        Returns:
            True if tablet device, False otherwise
        """
        if not user_agent:
            return False

        user_agent = user_agent.lower()
        return bool(self.tablet_regex.search(user_agent))

    def is_desktop(self, user_agent: Optional[str] = None) -> bool:
        """
        Detect if the request is from a desktop device.

        Args:
            user_agent: User-Agent string (if None, will attempt to get from request)

        Returns:
            True if desktop device, False otherwise
        """
        return not (self.is_mobile(user_agent) or self.is_tablet(user_agent))

    def get_device_type(self, user_agent: Optional[str] = None) -> str:
        """
        Get device type string.

        Args:
            user_agent: User-Agent string (if None, will attempt to get from request)

        Returns:
            'mobile', 'tablet', or 'desktop'
        """
        if self.is_mobile(user_agent):
            return 'mobile'
        elif self.is_tablet(user_agent):
            return 'tablet'
        else:
            return 'desktop'


# Global instance for easy importing
device_detector = DeviceDetector()


def detect_device_type(user_agent: Optional[str] = None) -> str:
    """
    Convenience function to detect device type.

    Args:
        user_agent: User-Agent string (if None, will attempt to get from request)

    Returns:
        'mobile', 'tablet', or 'desktop'
    """
    return device_detector.get_device_type(user_agent)


def is_mobile_device(user_agent: Optional[str] = None) -> bool:
    """
    Convenience function to check if device is mobile.

    Args:
        user_agent: User-Agent string (if None, will attempt to get from request)

    Returns:
        True if mobile device, False otherwise
    """
    return device_detector.is_mobile(user_agent)


def is_tablet_device(user_agent: Optional[str] = None) -> bool:
    """
    Convenience function to check if device is tablet.

    Args:
        user_agent: User-Agent string (if None, will attempt to get from request)

    Returns:
        True if tablet device, False otherwise
    """
    return device_detector.is_tablet(user_agent)


def is_desktop_device(user_agent: Optional[str] = None) -> bool:
    """
    Convenience function to check if device is desktop.

    Args:
        user_agent: User-Agent string (if None, will attempt to get from request)

    Returns:
        True if desktop device, False otherwise
    """
    return device_detector.is_desktop(user_agent)


# For backward compatibility and easy access
__all__ = [
    'DeviceDetector',
    'device_detector',
    'detect_device_type',
    'is_mobile_device',
    'is_tablet_device',
    'is_desktop_device'
]
