#FullCircleMUD/typeclasses/utils/dice_roller.py

from random import randint

class DiceRoller:

    def roll(self, roll_string, max_number=10):
        """
        NOTE: In evennia/contribs/rpg/dice/ is a more powerful dice roller with
        more features, such as modifiers, secret rolls etc. This is much simpler and only
        gets a simple sum of normal rpg-dice.

        Args:
            roll_string (str): A roll using standard rpg syntax, <number>d<diesize>, like
                1d6, 2d10 etc. Max die-size is 1000.
            max_number (int): The max number of dice to roll. Defaults to 10, which is usually
                more than enough.

        Returns:
            int: The rolled result - sum of all dice rolled.

        Raises:
            TypeError: If roll_string is not on the right format or otherwise doesn't validate.

        Notes:
            Since we may see user input to this function, we make sure to validate the inputs (we
            wouldn't bother much with that if it was just for developer use).

        """
        max_diesize = 1000
        roll_string = roll_string.lower().replace(" ", "")
        if "d" not in roll_string:
            raise TypeError(
                f"Dice roll '{roll_string}' was not recognized. Must be `<number>d<dicesize>[+/-modifier]`."
            )
        number, rest = roll_string.split("d", 1)

        # Parse optional +/- modifier after die size
        modifier = 0
        for sep in ("+", "-"):
            if sep in rest:
                diesize_str, mod_str = rest.split(sep, 1)
                try:
                    modifier = int(sep + mod_str)
                except ValueError:
                    raise TypeError(f"Modifier in '{roll_string}' must be numerical.")
                rest = diesize_str
                break

        try:
            number = int(number)
            diesize = int(rest)
        except Exception:
            raise TypeError(f"The number and dice-size of '{roll_string}' must be numerical.")
        if 0 < number > max_number:
            raise TypeError(f"Invalid number of dice rolled (must be between 1 and {max_number})")
        if 0 < diesize > max_diesize:
            raise TypeError(f"Invalid die-size used (must be between 1 and {max_diesize} sides)")

        # Roll dice and apply modifier
        return sum(randint(1, diesize) for _ in range(number)) + modifier
            
       
    def roll_with_advantage_or_disadvantage(self, advantage=False, disadvantage=False):
        
        if not (advantage or disadvantage) or (advantage and disadvantage):
            # normal roll - advantage/disadvantage not set or they cancel 
            # each other out 
            return self.roll("1d20")
        elif advantage:
             # highest of two d20 rolls
             return max(self.roll("1d20"), self.roll("1d20"))
        else:
             # disadvantage - lowest of two d20 rolls 
             return min(self.roll("1d20"), self.roll("1d20"))
       
       
    def roll_random_table(self, dieroll, table_choices): 
        """ 
        Args: 
             dieroll (str): A die roll string, like "1d20".
             table_choices (iterable): A list of either single elements or 
                of tuples. 

                Example Table rolled against a d8:

                        effect_table = (
                            ("1-2", "dead"),
                            ("3", "effect1"),
                            ("4", "effect2"),
                            ("5", "effect3"),
                            ("6", "effect4"),
                            ("7", "effect5"),
                            ("8", "effect6"),
                        )

        Returns: 
            Any: A random result from the given list of choices.
            
        Raises:
            RuntimeError: If rolling dice giving results outside the table.
            
        """
        roll_result = self.roll(dieroll) 
        
        if isinstance(table_choices[0], (tuple, list)):
            # the first element is a tuple/list; treat as on the form [("1-5", "item"),...]
            for (valrange, choice) in table_choices:
                minval, *maxval = valrange.split("-", 1)
                minval = abs(int(minval))
                maxval = abs(int(maxval[0]) if maxval else minval)
                
                if minval <= roll_result <= maxval:
                    return choice 
                
            # if we get here we must have set a dieroll producing a value 
            # outside of the table boundaries - raise error
            raise RuntimeError("roll_random_table: Invalid die roll")
        else:
            # a simple regular list
            roll_result = max(1, min(len(table_choices), roll_result))
            return table_choices[roll_result - 1]





    # from OG dice roller in tutorial, seperate out into rules???
    """
    def saving_throw(...):
        # do a saving throw against a specific target number
        
    def opposed_saving_throw(...):
        # do an opposed saving throw against a target's defense

    def morale_check(...):
        # roll a 2d6 morale check for a target
        
    def heal_from_rest(...):
        # heal 1d8 when resting+eating, but not more than max value.
        
    def roll_death(...):
        # roll to determine penalty when hitting 0 HP. 
    """
        
       
dice = DiceRoller()