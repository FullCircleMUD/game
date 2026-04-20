from enum import Enum


class Size(str, Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"


_SIZE_VALUE = {
    Size.TINY: 1,
    Size.SMALL: 2,
    Size.MEDIUM: 3,
    Size.LARGE: 4,
    Size.HUGE: 5,
    Size.GARGANTUAN: 6,
}


def size_value(size):
    """Return numeric value for a size (1=tiny .. 6=gargantuan).

    Accepts Size enum members or raw strings.
    """
    return _SIZE_VALUE[Size(size)]


def bigger_than(check_size, reference_size):
    """True if check_size is strictly larger than reference_size."""
    return size_value(check_size) > size_value(reference_size)


def smaller_than(check_size, reference_size):
    """True if check_size is strictly smaller than reference_size."""
    return size_value(check_size) < size_value(reference_size)
