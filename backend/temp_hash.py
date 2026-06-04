from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

print("user:", password_hash.hash("sema-eco"))
print("admin:", password_hash.hash("KatkaKlenkova"))