import sqlite3
import unittest

from load_data import DB_PATH
from pipeline import get_responder_frequencies


class ResponderFrequencyTests(unittest.TestCase):
    def test_returns_each_sample_population_observation(self):
        with sqlite3.connect(DB_PATH) as connection:
            frequencies = get_responder_frequencies(connection)

        self.assertEqual(
            frequencies["response"].value_counts().to_dict(),
            {"yes": 4_965, "no": 4_875},
        )


if __name__ == "__main__":
    unittest.main()
