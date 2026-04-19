from fastapi_users.password import PasswordHelper
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

password_helper = PasswordHelper(
    password_hash=PasswordHash((Argon2Hasher(memory_cost=19456, time_cost=2, parallelism=1),)),
)
