import os
import json
import tempfile
import unittest
from unittest.mock import patch
from main_standalone import (
    parse_int_env,
    get_validated_env_config,
    validate_config_file,
    validate_all
)


class TestConfigValidation(unittest.TestCase):

    def setUp(self):
        # Save original env
        self.original_env = os.environ.copy()

    def tearDown(self):
        # Restore original env
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_parse_int_env_valid(self):
        os.environ['TEST_INT'] = '10'
        self.assertEqual(parse_int_env('TEST_INT', 5), 10)

    def test_parse_int_env_default(self):
        os.environ.pop('TEST_INT', None)
        self.assertEqual(parse_int_env('TEST_INT', 5), 5)

    def test_parse_int_env_invalid(self):
        os.environ['TEST_INT'] = 'abc'
        with self.assertRaises(ValueError) as ctx:
            parse_int_env('TEST_INT', 5)
        self.assertIn("must be an integer", str(ctx.exception))

    def test_get_validated_env_config_defaults(self):
        config = get_validated_env_config()
        self.assertEqual(config['run_interval_hours'], 24)
        self.assertEqual(config['random_insert_min'], 1)
        self.assertEqual(config['random_insert_max'], 10)
        self.assertEqual(config['max_data_limit'], 50)
        self.assertEqual(config['target_data_count'], 30)
        self.assertEqual(config['max_runs_before_restart'], 0)

    def test_get_validated_env_config_invalid_run_interval(self):
        os.environ['RUN_INTERVAL_HOURS'] = '0'
        with self.assertRaises(ValueError) as ctx:
            get_validated_env_config()
        self.assertIn("RUN_INTERVAL_HOURS must be greater than 0", str(ctx.exception))

    def test_get_validated_env_config_invalid_insert_min(self):
        os.environ['RANDOM_INSERT_MIN'] = '0'
        with self.assertRaises(ValueError) as ctx:
            get_validated_env_config()
        self.assertIn("RANDOM_INSERT_MIN must be at least 1", str(ctx.exception))

    def test_get_validated_env_config_invalid_insert_range(self):
        os.environ['RANDOM_INSERT_MIN'] = '10'
        os.environ['RANDOM_INSERT_MAX'] = '5'
        with self.assertRaises(ValueError) as ctx:
            get_validated_env_config()
        self.assertIn("must be greater than or equal to RANDOM_INSERT_MIN", str(ctx.exception))

    def test_get_validated_env_config_invalid_max_data_limit(self):
        os.environ['MAX_DATA_LIMIT'] = '-1'
        with self.assertRaises(ValueError) as ctx:
            get_validated_env_config()
        self.assertIn("MAX_DATA_LIMIT must be greater than 0", str(ctx.exception))

    def test_get_validated_env_config_invalid_target_data_count(self):
        os.environ['MAX_DATA_LIMIT'] = '50'
        os.environ['TARGET_DATA_COUNT'] = '60'
        with self.assertRaises(ValueError) as ctx:
            get_validated_env_config()
        self.assertIn("cannot exceed MAX_DATA_LIMIT", str(ctx.exception))

    def test_validate_config_file_missing(self):
        with self.assertRaises(ValueError) as ctx:
            validate_config_file("non_existent_config.json")
        self.assertIn("not found", str(ctx.exception))

    def test_validate_config_file_invalid_json(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write("{ invalid json }")
            fname = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                validate_config_file(fname)
            self.assertIn("Error parsing", str(ctx.exception))
        finally:
            os.remove(fname)

    def test_validate_config_file_not_list(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            json.dump({"name": "DB1"}, f)
            fname = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                validate_config_file(fname)
            self.assertIn("must be a JSON array", str(ctx.exception))
        finally:
            os.remove(fname)

    def test_validate_config_file_empty_list(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            json.dump([], f)
            fname = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                validate_config_file(fname)
            self.assertIn("is empty", str(ctx.exception))
        finally:
            os.remove(fname)

    def test_validate_config_file_missing_credentials(self):
        data = [{
            "name": "DB1",
            "supabase_url": "https://test.supabase.co"
        }]
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            json.dump(data, f)
            fname = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                validate_config_file(fname)
            self.assertIn("must specify either 'supabase_key' or a valid 'supabase_key_env'", str(ctx.exception))
        finally:
            os.remove(fname)

    def test_validate_config_file_missing_env_key(self):
        data = [{
            "name": "DB1",
            "supabase_url": "https://test.supabase.co",
            "supabase_key_env": "MISSING_ENV_VAR"
        }]
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            json.dump(data, f)
            fname = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                validate_config_file(fname)
            self.assertIn("references environment variable 'MISSING_ENV_VAR' which is not set or empty", str(ctx.exception))
        finally:
            os.remove(fname)

    def test_validate_config_file_valid(self):
        os.environ['MY_SUPABASE_KEY'] = 'secret-key-123'
        data = [
            {
                "name": "DB1",
                "supabase_url": "https://test1.supabase.co",
                "supabase_key": "direct-key-123"
            },
            {
                "name": "DB2",
                "supabase_url": "https://test2.supabase.co",
                "supabase_key_env": "MY_SUPABASE_KEY"
            }
        ]
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            json.dump(data, f)
            fname = f.name
        try:
            configs = validate_config_file(fname)
            self.assertEqual(len(configs), 2)
            self.assertEqual(configs[0]['name'], "DB1")
            self.assertEqual(configs[1]['supabase_key_env'], "MY_SUPABASE_KEY")
        finally:
            os.remove(fname)


if __name__ == "__main__":
    unittest.main()
