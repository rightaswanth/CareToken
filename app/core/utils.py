import secrets
import string
import re

def generate_password():
    adjectives = ["Happy", "Sunny", "Clever", "Brave", "Calm", "Eager", "Fancy", "Jolly", "Kind", "Lively"]
    nouns = ["Tiger", "Lion", "Eagle", "Panda", "Bear", "Wolf", "Fox", "Hawk", "Owl", "Deer"]
    
    adj = secrets.choice(adjectives)
    noun = secrets.choice(nouns)
    number = secrets.randbelow(1000)
    
    return f"{adj}-{noun}-{number:03d}"

def generate_username(name: str):
    # Simple username generation: lowercase name + random suffix
    base = name.lower().replace(" ", "")[:10]
    suffix = ''.join(secrets.choice(string.digits) for i in range(4))
    return f"{base}{suffix}"

def generate_slug(name: str) -> str:
    # Convert to lowercase
    slug = name.lower()
    # Remove special characters
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove trailing hyphens
    slug = slug.strip('-')
    # Add random suffix to ensure uniqueness
    suffix = ''.join(secrets.choice(string.digits) for i in range(4))
    return f"{slug}-{suffix}"
