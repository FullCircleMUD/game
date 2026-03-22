from evennia import DefaultObject

class Area(DefaultObject):
    """
    Logical container for multiple AreaRooms.
    Tracks positions and inter-room mechanics.
    """
    def at_object_creation(self):
        self.db.rooms = []          # list of rooms in the area
        self.db.grid_positions = {} # optional mapping: (row, col) -> room

    def add_room(self, room, position=None):
        self.db.rooms.append(room)
        room.db.area = self
        if position:
            self.db.grid_positions[position] = room

    def get_room_at(self, position):
        return self.db.grid_positions.get(position)