import secrets
import string

def generate_secure_cookie_key(length=64):
    """
    Generates a cryptographically secure random string suitable for a cookie key.

    Args:
        length (int): The desired length of the key. A longer key is more secure.
                      64 characters (32 bytes converted to hex) is a good starting point.

    Returns:
        str: A randomly generated, secure string.
    """
    # You can use secrets.token_urlsafe() for a URL-safe string
    # or secrets.token_hex() for a hexadecimal string.
    # For a cookie key, token_urlsafe() is often a good choice as it's base64 encoded
    # and generally safe for various contexts.
    return secrets.token_urlsafe(length)

# Example usage:
# Generate a key (e.g., 64 characters long, which is 64 bytes converted to URL-safe base64)
cookie_key = generate_secure_cookie_key(64)
print(f"Generated Cookie Key: {cookie_key}")
print(f"Length: {len(cookie_key)}")

# Example using token_hex for a specific length (e.g., 32 bytes = 64 hex characters)
hex_key = secrets.token_hex(32)
print(f"Generated Hex Key: {hex_key}")
print(f"Length: {len(hex_key)}")