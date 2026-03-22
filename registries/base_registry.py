class BaseRegistry:
    """
    Generic registry for any type of object keyed by a string.
    """
    _registry = {}

    @classmethod
    def register(cls, obj):
        key = obj.key.lower()
        if key in cls._registry:
            raise ValueError(f"{cls.__name__} already has a '{key}' registered.")
        cls._registry[key] = obj

    @classmethod
    def get(cls, key):
        return cls._registry.get(key.lower())

    @classmethod
    def list_keys(cls):
        return list(cls._registry.keys())

    @classmethod
    def list_items(cls):
        return cls._registry.items()
        