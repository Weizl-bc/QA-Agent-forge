import unittest
from datetime import datetime
from unittest.mock import patch

from agent_core.common.logging_config import _add_local_timestamp


class LoggingConfigTest(unittest.TestCase):
    def test_timestamp_uses_configured_timezone(self) -> None:
        with patch.dict(
            "os.environ",
            {"LOG_TIMEZONE": "Asia/Shanghai"},
        ):
            event = _add_local_timestamp(None, "info", {})

        timestamp = datetime.fromisoformat(event["timestamp"])
        self.assertEqual(
            timestamp.utcoffset().total_seconds(),
            8 * 60 * 60,
        )


if __name__ == "__main__":
    unittest.main()
