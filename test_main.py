import json
import os
import unittest
from unittest.mock import MagicMock, patch

import main_standalone


class TestSupabaseZombi(unittest.TestCase):

    @patch("main_standalone.create_client")
    def test_delete_random_entry_success(self, mock_create_client):
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Setup table select & delete response
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # select response
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[{"id": 1, "name": "test"}])
        mock_table.select.return_value = mock_select

        # delete response
        mock_delete_filter = MagicMock()
        mock_delete_filter.execute.return_value = MagicMock(data=[{"id": 1, "name": "test"}])
        mock_delete_builder = MagicMock()
        mock_delete_builder.eq.return_value = mock_delete_filter
        mock_table.delete.return_value = mock_delete_builder

        client_wrapper = main_standalone.SupabaseClient("http://fake.url", "fake_key", "KeepAlive")
        result = client_wrapper.delete_random_entry()

        self.assertTrue(result)
        mock_table.delete().eq.assert_called_with("id", 1)

    @patch("main_standalone.create_client")
    def test_delete_random_entry_zero_deleted(self, mock_create_client):
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[{"id": 1, "name": "test"}])
        mock_table.select.return_value = mock_select

        # delete response returns empty data (0 rows deleted)
        mock_delete_filter = MagicMock()
        mock_delete_filter.execute.return_value = MagicMock(data=[])
        mock_delete_builder = MagicMock()
        mock_delete_builder.eq.return_value = mock_delete_filter
        mock_table.delete.return_value = mock_delete_builder

        client_wrapper = main_standalone.SupabaseClient("http://fake.url", "fake_key", "KeepAlive")
        result = client_wrapper.delete_random_entry()

        self.assertFalse(result)

    @patch("main_standalone.send_telegram_message")
    @patch("main_standalone.SupabaseClient")
    def test_run_keepalive_full_success_cleanup(self, mock_supabase_client_cls, mock_send_tg):
        mock_client = MagicMock()
        mock_supabase_client_cls.return_value = mock_client

        # Insert succeeds
        mock_client.insert_random_name.return_value = True

        # Initial count 55, target 30 -> num_deletes = 25
        # Post-delete count 30
        mock_client.get_table_count.side_effect = [55, 30]
        # delete_random_entry returns True for all 25 calls
        mock_client.delete_random_entry.return_value = True

        config_data = [{"name": "Test DB", "supabase_url": "http://test.url", "supabase_key": "key123"}]

        with patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(config_data))), \
             patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "123"}), \
             patch("main_standalone.time.sleep"), \
             self.assertLogs(level="INFO") as log_cm:

            main_standalone.run_keepalive()

            # Check logs
            log_output = "\n".join(log_cm.output)
            self.assertIn("✓ SUCCESS | #30 data | Inserted:", log_output)
            self.assertIn("Deleted: 25/25", log_output)
            self.assertIn("✅ All run complete", log_output)

            # Check telegram report
            mock_send_tg.assert_called_once()
            tg_msg = mock_send_tg.call_args[0][2]
            self.assertIn("✅ All databases updated successfully!", tg_msg)

    @patch("main_standalone.send_telegram_message")
    @patch("main_standalone.SupabaseClient")
    def test_run_keepalive_partial_success_cleanup(self, mock_supabase_client_cls, mock_send_tg):
        mock_client = MagicMock()
        mock_supabase_client_cls.return_value = mock_client

        mock_client.insert_random_name.return_value = True

        # Initial count 52, target 30 -> num_deletes = 22
        # Post-delete count 40
        mock_client.get_table_count.side_effect = [52, 40]
        # Only first 10 deletes succeed, rest fail
        mock_client.delete_random_entry.side_effect = [True] * 10 + [False] * 12

        config_data = [{"name": "Test DB", "supabase_url": "http://test.url", "supabase_key": "key123"}]

        with patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(config_data))), \
             patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "123"}), \
             patch("main_standalone.time.sleep"), \
             self.assertLogs(level="INFO") as log_cm:

            main_standalone.run_keepalive()

            log_output = "\n".join(log_cm.output)
            self.assertIn("⚠️  PARTIAL SUCCESS | #40 data | Inserted:", log_output)
            self.assertIn("Deleted: 10/22", log_output)
            self.assertIn("⚠️ All run complete with warnings", log_output)

            mock_send_tg.assert_called_once()
            tg_msg = mock_send_tg.call_args[0][2]
            self.assertIn("⚠️ All databases updated with warnings", tg_msg)
            self.assertIn("Warnings: Test DB (partial cleanup: 10/22)", tg_msg)

    @patch("main_standalone.send_telegram_message")
    @patch("main_standalone.SupabaseClient")
    def test_run_keepalive_zero_deleted_cleanup(self, mock_supabase_client_cls, mock_send_tg):
        mock_client = MagicMock()
        mock_supabase_client_cls.return_value = mock_client

        mock_client.insert_random_name.return_value = True

        # Initial count 52, target 30 -> num_deletes = 22
        # Post-delete count 52
        mock_client.get_table_count.side_effect = [52, 52]
        # All deletes fail (0 deleted)
        mock_client.delete_random_entry.return_value = False

        config_data = [{"name": "Test DB", "supabase_url": "http://test.url", "supabase_key": "key123"}]

        with patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(config_data))), \
             patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "123"}), \
             patch("main_standalone.time.sleep"), \
             self.assertLogs(level="INFO") as log_cm:

            main_standalone.run_keepalive()

            log_output = "\n".join(log_cm.output)
            self.assertIn("⚠️  CLEANUP FAILED | #52 data | Inserted:", log_output)
            self.assertIn("Deleted: 0/22", log_output)
            self.assertIn("⚠️ All run complete with warnings", log_output)

            mock_send_tg.assert_called_once()
            tg_msg = mock_send_tg.call_args[0][2]
            self.assertIn("⚠️ All databases updated with warnings", tg_msg)
            self.assertIn("Warnings: Test DB (cleanup failed: 0/22)", tg_msg)


if __name__ == "__main__":
    unittest.main()
