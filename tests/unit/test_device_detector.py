"""
Unit tests for the device detection utility (utils/device_detector.py).

Covers DeviceDetector class methods and module-level convenience functions.
User-Agent strings are representative samples for each device category.
"""

import pytest

from utils.device_detector import (
    DeviceDetector,
    device_detector,
    detect_device_type,
    is_mobile_device,
    is_tablet_device,
    is_desktop_device,
)

# ---------------------------------------------------------------------------
# Sample User-Agent strings
# ---------------------------------------------------------------------------

MOBILE_UAS = [
    # iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    # Android phone
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
    # Windows Phone
    "Mozilla/5.0 (compatible; MSIE 10.0; Windows Phone 8.0; Trident/6.0)",
    # BlackBerry
    "Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en-US) "
    "AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.0.0.187 Mobile Safari/534.11+",
    # Opera Mini
    "Opera/9.80 (J2ME/MIDP; Opera Mini/9.80; U; en) Presto/2.12.407 Version/12.50",
]

TABLET_UAS = [
    # iPad
    "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    # Android tablet (no 'mobile' in UA)
    "Mozilla/5.0 (Linux; Android 11; SM-T870) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    # Kindle Fire
    "Mozilla/5.0 (Linux; U; Android 2.3.4; en-us; Kindle Fire Build/GINGERBREAD) "
    "AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    # Nexus 7
    "Mozilla/5.0 (Linux; Android 4.3; Nexus 7 Build/JSS15Q) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.72 Safari/537.36",
]

DESKTOP_UAS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/112.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.0.0",
]


# ---------------------------------------------------------------------------
# DeviceDetector class
# ---------------------------------------------------------------------------


class TestDeviceDetectorMobile:
    """is_mobile() returns True for phone UAs and False for others."""

    @pytest.fixture(autouse=True)
    def detector(self):
        self.dd = DeviceDetector()

    @pytest.mark.parametrize("ua", MOBILE_UAS)
    def test_phone_ua_is_mobile(self, ua):
        assert self.dd.is_mobile(ua) is True

    @pytest.mark.parametrize("ua", TABLET_UAS)
    def test_tablet_ua_not_mobile(self, ua):
        assert self.dd.is_mobile(ua) is False

    @pytest.mark.parametrize("ua", DESKTOP_UAS)
    def test_desktop_ua_not_mobile(self, ua):
        assert self.dd.is_mobile(ua) is False

    def test_none_ua_not_mobile(self):
        assert self.dd.is_mobile(None) is False

    def test_empty_ua_not_mobile(self):
        assert self.dd.is_mobile("") is False


class TestDeviceDetectorTablet:
    """is_tablet() returns True for tablet UAs and False for others."""

    @pytest.fixture(autouse=True)
    def detector(self):
        self.dd = DeviceDetector()

    @pytest.mark.parametrize("ua", TABLET_UAS)
    def test_tablet_ua_is_tablet(self, ua):
        assert self.dd.is_tablet(ua) is True

    @pytest.mark.parametrize("ua", MOBILE_UAS)
    def test_phone_ua_not_tablet(self, ua):
        assert self.dd.is_tablet(ua) is False

    @pytest.mark.parametrize("ua", DESKTOP_UAS)
    def test_desktop_ua_not_tablet(self, ua):
        assert self.dd.is_tablet(ua) is False

    def test_none_ua_not_tablet(self):
        assert self.dd.is_tablet(None) is False

    def test_empty_ua_not_tablet(self):
        assert self.dd.is_tablet("") is False


class TestDeviceDetectorDesktop:
    """is_desktop() returns True when device is neither mobile nor tablet."""

    @pytest.fixture(autouse=True)
    def detector(self):
        self.dd = DeviceDetector()

    @pytest.mark.parametrize("ua", DESKTOP_UAS)
    def test_desktop_ua_is_desktop(self, ua):
        assert self.dd.is_desktop(ua) is True

    @pytest.mark.parametrize("ua", MOBILE_UAS)
    def test_phone_ua_not_desktop(self, ua):
        assert self.dd.is_desktop(ua) is False

    @pytest.mark.parametrize("ua", TABLET_UAS)
    def test_tablet_ua_not_desktop(self, ua):
        assert self.dd.is_desktop(ua) is False

    def test_none_ua_is_desktop(self):
        # No UA → treated as desktop (safe fallback)
        assert self.dd.is_desktop(None) is True

    def test_empty_ua_is_desktop(self):
        assert self.dd.is_desktop("") is True


class TestDeviceDetectorGetDeviceType:
    """get_device_type() returns the correct string label."""

    @pytest.fixture(autouse=True)
    def detector(self):
        self.dd = DeviceDetector()

    @pytest.mark.parametrize("ua", MOBILE_UAS)
    def test_mobile_ua_returns_mobile(self, ua):
        assert self.dd.get_device_type(ua) == "mobile"

    @pytest.mark.parametrize("ua", TABLET_UAS)
    def test_tablet_ua_returns_tablet(self, ua):
        assert self.dd.get_device_type(ua) == "tablet"

    @pytest.mark.parametrize("ua", DESKTOP_UAS)
    def test_desktop_ua_returns_desktop(self, ua):
        assert self.dd.get_device_type(ua) == "desktop"

    def test_none_ua_returns_desktop(self):
        assert self.dd.get_device_type(None) == "desktop"

    def test_return_values_are_strings(self):
        for ua in MOBILE_UAS + TABLET_UAS + DESKTOP_UAS:
            result = self.dd.get_device_type(ua)
            assert isinstance(result, str)
            assert result in ("mobile", "tablet", "desktop")


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    """Module-level helpers delegate correctly to the global device_detector."""

    @pytest.mark.parametrize("ua", MOBILE_UAS)
    def test_is_mobile_device_true_for_phones(self, ua):
        assert is_mobile_device(ua) is True

    @pytest.mark.parametrize("ua", DESKTOP_UAS)
    def test_is_mobile_device_false_for_desktop(self, ua):
        assert is_mobile_device(ua) is False

    @pytest.mark.parametrize("ua", TABLET_UAS)
    def test_is_tablet_device_true_for_tablets(self, ua):
        assert is_tablet_device(ua) is True

    @pytest.mark.parametrize("ua", MOBILE_UAS)
    def test_is_tablet_device_false_for_phones(self, ua):
        assert is_tablet_device(ua) is False

    @pytest.mark.parametrize("ua", DESKTOP_UAS)
    def test_is_desktop_device_true_for_desktop(self, ua):
        assert is_desktop_device(ua) is True

    @pytest.mark.parametrize("ua", TABLET_UAS)
    def test_is_desktop_device_false_for_tablets(self, ua):
        assert is_desktop_device(ua) is False

    @pytest.mark.parametrize("ua", MOBILE_UAS)
    def test_detect_device_type_mobile(self, ua):
        assert detect_device_type(ua) == "mobile"

    @pytest.mark.parametrize("ua", TABLET_UAS)
    def test_detect_device_type_tablet(self, ua):
        assert detect_device_type(ua) == "tablet"

    @pytest.mark.parametrize("ua", DESKTOP_UAS)
    def test_detect_device_type_desktop(self, ua):
        assert detect_device_type(ua) == "desktop"


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


def test_global_device_detector_instance():
    """device_detector is a pre-built DeviceDetector instance."""
    assert isinstance(device_detector, DeviceDetector)
