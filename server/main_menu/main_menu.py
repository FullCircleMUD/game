from evennia.utils.evmenu import EvMenu


def node_puppet_char(account, raw_input, **kwargs):
    char_key = kwargs.get("char_key")
    session = kwargs.get("session")

    if not char_key:
        account.msg("\nNo character specified!")
        return "node_main_menu"

    # Find the character on this account
    character = next((c for c in account.characters.all() if c.key.lower() == char_key.lower()), None)
    if not character:
        account.msg(f"\nCharacter '{char_key}' not found!")
        return "node_main_menu"

    #text = f"\nYou are now puppeting {character.key}."
    
    account.msg(f"\nHas Sessions attribute: {hasattr(account, "sessions")}")
    account.msg(f"\nNum Sessions: {len(account.sessions.get())}")
    session = account.sessions.get()[0]
    account.msg(f"\nSession: {session}")
    account.puppet_object(session, character)

    #EvMenu.close_menu(account)
 
    return "bollocks", None


def _quit_game(account, raw_input, **kwargs):
    # 'quit' is the Evennia builtin quit command
    account.execute_cmd("quit")
    return "node_end"  # exit the menu

def node_chargen_1(account, raw_input, **kwargs):
    text = "character creation process - to be completed"
    options = (
        {
            "key": ("done"), 
            "desc": "Simulate finishing building character", 
            "goto": ("node_main_menu")
        }, 
    )
    return text, options

def node_main_menu(account, raw_input, **kwargs):
    
    text = "Main Menu"
    characters = account.characters.all()

    """
    if not characters:
        char_text = "You have no characters."
    else:
        char_list = "\n".join(f"- {char.key} (#{char.id})" for char in characters)
        char_text = f"Your characters:\n\n{char_list}"
    """

    options_list = []
    keycount = 1
    create_key = "\nc"

    max_length = 15
    for char in characters:
        if len(char.key) > max_length:
            max_length = len(char.key)

    # create a character listing
    for char in characters:
        #classes = char.db.classes
        char_desc = f"{char.key:<{max_length}}  Warrior 3, Cleric 1"

        options_list.append({
            "key": str(keycount),
            "desc" : char_desc,
            "goto" : ("node_puppet_char", {"char_key": char.key})})
        
        keycount += 1

    # add a create character option
    options_list.append({
            "key": f"{create_key}",
            "desc" : "Create a new character",
            "goto" : ("node_chargen_1", {})})

    # add an exit option
    options_list.append({
            "key": "x",
            "desc" : "Exit Game",
            "goto" : (_quit_game, {})})

    options = tuple(options_list)

    return text, options

def node_end(account, raw_input, **kwargs):
    return "XXXXXX - WORK OUT HOW TO STOP THE DOUBLE RENDER OF THE ROOM", None  # empty options ends the menu
