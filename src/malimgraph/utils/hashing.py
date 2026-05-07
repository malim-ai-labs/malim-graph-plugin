import hashlib


def entity_id(entity_type: str, label: str) -> str:
    """Stable entity ID — same type+label always produces the same ID."""
    key = f"{entity_type}:{label}".lower().strip()
    digest = hashlib.md5(key.encode()).hexdigest()[:8]
    return f"e_{digest}"


def relationship_id(source_id: str, rel_type: str, target_id: str) -> str:
    """Stable relationship ID from source, type, and target."""
    key = f"{source_id}:{rel_type}:{target_id}".lower()
    digest = hashlib.md5(key.encode()).hexdigest()[:8]
    return f"r_{digest}"
