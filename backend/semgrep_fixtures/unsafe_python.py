import hashlib
import pickle
import subprocess

import httpx


API_KEY = "sk_live_super_secret_12345"


async def run_query(cursor, user_input):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_input}")
    hashlib.md5(user_input.encode()).hexdigest()
    async with httpx.AsyncClient(verify=False):
        pass
    subprocess.run(f"echo {user_input}", shell=True)
    pickle.loads(user_input)
