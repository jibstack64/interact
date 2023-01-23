import cryptography.fernet as fernet
print(fernet.Fernet.generate_key().decode())