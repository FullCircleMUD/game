# FullCircleMUD/tests/utils_tests/test_dice_roller.py

#TO RUN INDIVIDUAL TEST:
# IN FullCircleMUD Folder:  evennia test --settings settings.py tests.utils_tests.test_dice_roller

# TO RUN ALL TESTS:
# IN FullCircleMUD Folder:  evennia test --settings settings.py tests

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from utils.dice_roller import dice
from unittest.mock import patch, call


test_tables = {
    "test_table": [
        "result1",
        "result2",
        "result3",
        "result4",
        "result5",
    ],

}

class TestDiceRoller(EvenniaTest):

    def create_script(self):
        pass

    def test_dice_roll_D1(self):
        self.assertTrue(dice.roll("2d1") == 2)
        self.assertTrue(dice.roll("5d1") == 5)

    @patch("utils.dice_roller.randint")
    def test_roll_with_mock(self, mock_randint):
        mock_randint.return_value = 4
        self.assertEqual(dice.roll("1d4"), 4)
        self.assertEqual(dice.roll("2d6"), 2 * 4)
        self.assertEqual(dice.roll("3d8"), 3 * 4)

    @patch("utils.dice_roller.randint")
    def test_roll_with_positive_modifier(self, mock_randint):
        mock_randint.return_value = 3
        self.assertEqual(dice.roll("1d6+2"), 5)
        self.assertEqual(dice.roll("2d6+5"), 11)

    @patch("utils.dice_roller.randint")
    def test_roll_with_negative_modifier(self, mock_randint):
        mock_randint.return_value = 4
        self.assertEqual(dice.roll("1d8-1"), 3)
        self.assertEqual(dice.roll("2d6-3"), 5)

    def test_roll_modifier_with_d1(self):
        self.assertEqual(dice.roll("1d1+3"), 4)
        self.assertEqual(dice.roll("2d1-1"), 1)

    def test_roll_modifier_invalid(self):
        with self.assertRaises(TypeError):
            dice.roll("1d6+abc")

    def test_roll_limits(self):
        with self.assertRaises(TypeError):
            dice.roll("101d6", max_number=10)  # too many die
        with self.assertRaises(TypeError):
            dice.roll("100")  # no d
        with self.assertRaises(TypeError):
            dice.roll("dummy")  # non-numerical
        with self.assertRaises(TypeError):
            dice.roll("Ad4")  # non-numerical
        with self.assertRaises(TypeError):
            dice.roll("1d10000")  # limit is d1000       

    
    @patch("utils.dice_roller.randint")
    def test_roll_with_advantage_disadvantage(self, mock_randint):
        mock_randint.return_value = 9

        # no advantage/disadvantage
        self.assertEqual(dice.roll_with_advantage_or_disadvantage(), 9)
        mock_randint.assert_called_once()
        mock_randint.reset_mock()

        # cancel each other out
        self.assertEqual(
            dice.roll_with_advantage_or_disadvantage(disadvantage=True, advantage=True),
            9,
        )
        mock_randint.assert_called_once()
        mock_randint.reset_mock()
    
        # run with advantage/disadvantage
        self.assertEqual(dice.roll_with_advantage_or_disadvantage(advantage=True), 9)
        mock_randint.assert_has_calls([call(1, 20), call(1, 20)])
        mock_randint.reset_mock()

        self.assertEqual(dice.roll_with_advantage_or_disadvantage(disadvantage=True), 9)
        mock_randint.assert_has_calls([call(1, 20), call(1, 20)])
        mock_randint.reset_mock()
    

    @patch("utils.dice_roller.randint")
    def test_roll_random_table(self, mock_randint):

        mock_randint.return_value = 2

        self.assertEqual(
            dice.roll_random_table("1d20", test_tables["test_table"]),
            "result2",
        )
        
        mock_randint.return_value = 3   
        self.assertEqual(
            dice.roll_random_table("1d20", test_tables["test_table"]),
            "result3",
        )

        mock_randint.return_value = 4  
        self.assertEqual(
            dice.roll_random_table("1d20", test_tables["test_table"]),
            "result4",
        )

        
        # testing faulty rolls outside of the table ranges
        mock_randint.return_value = 25
        self.assertEqual(
            dice.roll_random_table(
                "1d20", test_tables["test_table"]
            ),
            "result5",
        )
        mock_randint.return_value = -10
        self.assertEqual(
            dice.roll_random_table(
                "1d20", test_tables["test_table"]
            ),
            "result1",
        )
        