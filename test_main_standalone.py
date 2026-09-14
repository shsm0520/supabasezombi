import unittest
from unittest.mock import MagicMock, patch
import main_standalone
from main_standalone import SupabaseClient

class TestSupabaseClient(unittest.TestCase):
    @patch('main_standalone.create_client')
    def test_get_table_count(self, mock_create_client):
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Setup table mock
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_response = MagicMock()
        mock_response.count = 1500
        mock_table.select.return_value.execute.return_value = mock_response

        client = SupabaseClient("https://dummy.supabase.co", "dummy_key", "test_table")
        count = client.get_table_count()

        mock_table.select.assert_called_once_with("*", count="exact", head=True)
        self.assertEqual(count, 1500)

    @patch('main_standalone.create_client')
    def test_delete_excess_entries(self, mock_create_client):
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Mock select limit response for candidate IDs
        mock_select_response = MagicMock()
        mock_select_response.data = [{'id': 1}, {'id': 2}, {'id': 3}]
        mock_table.select.return_value.limit.return_value.execute.return_value = mock_select_response

        # Mock delete response
        mock_delete_response = MagicMock()
        mock_delete_response.data = [{'id': 1}, {'id': 2}, {'id': 3}]
        mock_table.delete.return_value.in_.return_value.execute.return_value = mock_delete_response

        client = SupabaseClient("https://dummy.supabase.co", "dummy_key", "test_table")
        deleted = client.delete_excess_entries(3)

        mock_table.select.assert_called_with("id")
        mock_table.delete.return_value.in_.assert_called_with("id", [1, 2, 3])
        self.assertEqual(deleted, 3)

    @patch('main_standalone.create_client')
    def test_delete_excess_entries_multiple_batches(self, mock_create_client):
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Batch 1 response
        mock_select_resp1 = MagicMock()
        mock_select_resp1.data = [{'id': i} for i in range(1, 3)]

        # Batch 2 response
        mock_select_resp2 = MagicMock()
        mock_select_resp2.data = [{'id': 3}]

        mock_table.select.return_value.limit.return_value.execute.side_effect = [
            mock_select_resp1,
            mock_select_resp2
        ]

        mock_del_resp1 = MagicMock()
        mock_del_resp1.data = [{'id': 1}, {'id': 2}]
        mock_del_resp2 = MagicMock()
        mock_del_resp2.data = [{'id': 3}]

        mock_table.delete.return_value.in_.return_value.execute.side_effect = [
            mock_del_resp1,
            mock_del_resp2
        ]

        client = SupabaseClient("https://dummy.supabase.co", "dummy_key", "test_table")
        deleted = client.delete_excess_entries(3, batch_size=2)

        self.assertEqual(deleted, 3)
        self.assertEqual(mock_table.delete.return_value.in_.call_count, 2)

if __name__ == '__main__':
    unittest.main()
