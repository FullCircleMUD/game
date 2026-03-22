# evmenu_login.py

from evennia.utils.evmenu import EvMenu

# --- Node: main menu ---
def node_main_menu(account, raw_input, **kwargs):
    """
    Main login menu node. Just shows numbered characters.
    """
    characters = account.characters.all()
    text = "Hello! Select a character:\n"
    
    options = []
    for i, char in enumerate(characters, start=1):
        options.append({
            "key": str(i),
            "desc": f"{char.key}",
            # goto a node that will puppet the character
            "goto": (node_puppet_char, {"char_key": char.key})
        })
    
    return text, tuple(options)


# --- Node: puppet the selected character ---
def node_puppet_char(account, raw_input, **kwargs):
    """
    This node runs after the user selects a character.
    Puppets IC via @ic, then exits the menu.
    """
    char_key = kwargs.get("char_key")
    if not char_key:
        account.msg("No character specified!")
        return None

    # Use Evennia's built-in @ic command to safely puppet
    account.execute_cmd(f"ic {char_key}")

    # Return None to exit the menu cleanly
    return None