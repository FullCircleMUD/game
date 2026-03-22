# FullCircleMUD/tests/utils_tests/test_get_obj_stats.py

#TO RUN INDIVIDUAL TEST:
# IN FullCircleMUD Folder:  evennia test --settings settings.py tests.utils_tests.test_utils

# TO RUN ALL TESTS:
# IN FullCircleMUD Folder:  evennia test --settings settings.py tests

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from utils.get_obj_stats import get_obj_stats

class TestUtils(EvenniaTest):

    def create_script(self):
        pass

    def test_get_obj_stats(self):
        # make a simple object to test with
        obj = create.create_object(
            key="testobj",
            attributes=(("desc", "A test object"),)
        )

        # run it through the function
        result = get_obj_stats(obj)

        # check that the result is what we expected
        self.assertEqual(
            result,
            """
|ctestobj|n
Value: ~|y10|n coins[Not carried]

A test object

Slots: |w1|n, Used from: |wbackpack|n
Quality: |w3|n, Uses: |winfinite|n
Attacks using |wstrength|n against |warmor|n
Damage roll: |w1d6|n
""".strip()
)