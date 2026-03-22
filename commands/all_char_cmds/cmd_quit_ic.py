from evennia import Command

class CmdQuitIC(Command):
    """
    Quit command for characters.
    Exits IC mode and returns to OOC/account mode.
    """

    key = "quit"
    locks = "cmd:all()"
    help_category = "System"

    def func(self):
        caller = self.caller

        if caller.scripts.get("combat_handler"):
            caller.msg("You can't quit while in combat! You must flee or end the fight first.")
            return

        session = self.session
        account = getattr(caller, "account", None)

        if not account:
            caller.msg("Cannot find your account.")
            return
        
        # If puppeting, unpuppet
        if account.get_puppet(session):
            # self.msg(self.at_look(target=self.characters, session=session), session=session)
            #account.msg(account.at_look())
            account.msg(account.at_look(target=account.characters, session=account.sessions.get()[0]))
            account.unpuppet_object(session)
            #caller.msg("You leave your character and return to OOC mode. Use quit again to leave the game.")



