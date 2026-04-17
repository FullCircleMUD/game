from enum import Enum


class ActorSize(str, Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"


_SIZE_VALUE = {
    ActorSize.TINY: 1,
    ActorSize.SMALL: 2,
    ActorSize.MEDIUM: 3,
    ActorSize.LARGE: 4,
    ActorSize.HUGE: 5,
    ActorSize.GARGANTUAN: 6,
}


def size_value(size):
    """Return numeric value for a size (1=tiny .. 6=gargantuan).

    Accepts ActorSize enum members or raw strings.
    """
    return _SIZE_VALUE[ActorSize(size)]


def bigger_than(check_size, reference_size):
    """True if check_size is strictly larger than reference_size."""
    return size_value(check_size) > size_value(reference_size)


def smaller_than(check_size, reference_size):
    """True if check_size is strictly smaller than reference_size."""
    return size_value(check_size) < size_value(reference_size)