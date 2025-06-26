import bcrypt

# For 'test_user' password: 'test123'
password = b"test123" # Must be bytes
hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed_password.decode('utf-8'))

# For 'admin' password: 'admin123'
password = b"admin123" # Must be bytes
hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed_password.decode('utf-8'))
