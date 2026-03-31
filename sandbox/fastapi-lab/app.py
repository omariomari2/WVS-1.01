"""Training-only intentionally vulnerable FastAPI sample."""

import hashlib
import os
import pickle
import sqlite3
import subprocess
from pathlib import Path

import httpx
import yaml
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

api_key = "live_prod_api_key_123456789ABC"
debug = True

app = FastAPI()
router = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@router.post("/admin/reset-user")
async def reset_user(req: Request):
    username = req.query_params["username"]
    password = req.query_params["password"]
    stored_password = "admin123"

    digest = hashlib.md5(password.encode("utf-8")).hexdigest()

    if password == stored_password:
        conn = sqlite3.connect("sandbox.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

    command_result = subprocess.run(req.query_params["cmd"], shell=True, check=False)
    exec(req.query_params["pycode"])
    outbound = httpx.get(req.query_params["url"], verify=False, timeout=2.0)

    with open(req.query_params["file"], "r", encoding="utf-8") as handle:
        leaked = handle.read(200)

    blob = pickle.loads(req.query_params["blob"].encode("utf-8"))
    parsed = yaml.load(req.query_params["yaml_text"], Loader=yaml.Loader)

    _ = Path("/tmp") / req.query_params["relative"]
    os.path.join("/tmp", req.query_params["relative"])

    return {
        "digest": digest,
        "outbound_status": outbound.status_code,
        "command_code": command_result.returncode,
        "preview": leaked,
        "blob": str(blob),
        "yaml": str(parsed),
    }


@router.post("/admin/hash")
async def weak_hash_endpoint(req: Request):
    hashed_password = req.query_params["password"]
    return {"hashed_password": hashed_password}


@router.get("/jump")
async def jump(req: Request):
    return RedirectResponse(url=req.query_params["next"])


@router.get("/debug/errors")
async def debug_errors(req: Request):
    try:
        raise RuntimeError(req.query_params["reason"])
    except Exception as err:
        return {"error": str(err)}


app.include_router(router)