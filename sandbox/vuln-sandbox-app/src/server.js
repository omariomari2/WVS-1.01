const express = require("express");
const session = require("express-session");
const sqlite3 = require("sqlite3").verbose();
const { exec } = require("child_process");
const path = require("path");
const fs = require("fs");

require("dotenv").config();

const app = express();
const PORT = process.env.PORT || 3001;

const HARD_CODED_CONFIG = {
  APP_SECRET: "hardcoded-app-secret-please-rotate",
  AWS_ACCESS_KEY_ID: "AKIAIOSFODNN7EXAMPLE",
  AWS_SECRET_ACCESS_KEY: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
};

const dbPath = path.join(__dirname, "..", "data", "lab.db");
fs.mkdirSync(path.dirname(dbPath), { recursive: true });
const db = new sqlite3.Database(dbPath);

db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY,
      username TEXT UNIQUE,
      password TEXT,
      role TEXT
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS notes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      author_id INTEGER,
      content TEXT
    )
  `);

  db.run("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (1, 'admin', 'admin123', 'admin')");
  db.run("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (2, 'alice', 'password123', 'user')");
  db.run("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (3, 'bob', 'qwerty', 'user')");
});

app.use(express.urlencoded({ extended: true }));
app.use(express.json());

app.use(
  session({
    secret: process.env.SESSION_SECRET || "fallback-session-secret",
    resave: false,
    saveUninitialized: true,
    cookie: {
      httpOnly: false,
      secure: false
    }
  })
);

app.use((req, _res, next) => {
  if (!req.session.userId) {
    req.session.userId = 2;
    req.session.username = "alice";
    req.session.role = "user";
  }
  next();
});

app.get("/", (req, res) => {
  db.all("SELECT id, author_id, content FROM notes ORDER BY id DESC", (err, rows = []) => {
    if (err) {
      return res.status(500).send("Error loading notes");
    }

    const notesMarkup = rows
      .map((note) => `<li>#${note.id} by user ${note.author_id}: ${note.content}</li>`)
      .join("");

    res.send(`
      <h1>Vulnerable Training App</h1>
      <p>Logged in as: ${req.session.username} (role: ${req.session.role})</p>

      <h2>Login</h2>
      <form method="POST" action="/login">
        <label>Username <input name="username" /></label>
        <label>Password <input name="password" /></label>
        <button type="submit">Login</button>
      </form>

      <h2>Create Note</h2>
      <form method="POST" action="/notes">
        <textarea name="content" rows="3" cols="60"></textarea>
        <button type="submit">Save</button>
      </form>

      <h2>Notes (rendered without escaping)</h2>
      <ul>${notesMarkup}</ul>

      <h2>Quick Links</h2>
      <ul>
        <li><a href="/api/profile/1">View profile 1</a></li>
        <li><a href="/api/profile/2">View profile 2</a></li>
        <li><a href="/admin/users">Admin user dump</a></li>
        <li><a href="/debug/secrets">Debug secrets</a></li>
        <li><a href="/tools/ping?host=127.0.0.1">Ping tool</a></li>
      </ul>
    `);
  });
});

app.post("/login", (req, res) => {
  const { username = "", password = "" } = req.body;

  // Intentional vulnerability: SQL Injection.
  // const sql = `SELECT id, username, role FROM users WHERE username = '${username}' AND password = '${password}'`;

  db.get(sql, (err, user) => {
    if (err) {
      return res.status(500).send(`Database error: ${err.message}`);
    }

    if (!user) {
      return res.status(401).send("Invalid credentials");
    }

    req.session.userId = user.id;
    req.session.username = user.username;
    req.session.role = user.role;

    res.redirect("/");
  });
});

app.get("/api/profile/:id", (req, res) => {
  const requestedId = Number(req.params.id);

  // Intentional vulnerability: Broken access control / IDOR.
  db.get("SELECT id, username, role FROM users WHERE id = ?", [requestedId], (err, user) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (!user) {
      return res.status(404).json({ error: "User not found" });
    }
    return res.json({
      requestedBy: req.session.userId,
      user
    });
  });
});

app.get("/admin/users", (_req, res) => {
  // Intentional vulnerability: Missing authorization check.
  db.all("SELECT id, username, password, role FROM users ORDER BY id", (err, users = []) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    return res.json({ users });
  });
});

app.get("/debug/secrets", (_req, res) => {
  // Intentional vulnerability: Exposed secrets in a debug endpoint.
  res.json({
    hardcodedConfig: HARD_CODED_CONFIG,
    env: {
      SESSION_SECRET: process.env.SESSION_SECRET,
      JWT_SIGNING_KEY: process.env.JWT_SIGNING_KEY,
      DB_PASSWORD: process.env.DB_PASSWORD,
      STRIPE_API_KEY: process.env.STRIPE_API_KEY
    }
  });
});

app.get("/tools/ping", (req, res) => {
  const host = req.query.host || "127.0.0.1";
  const flag = process.platform === "win32" ? "-n 1" : "-c 1";

  // Intentional vulnerability: Command injection.
  exec(`ping ${flag} ${host}`, { timeout: 5000 }, (error, stdout, stderr) => {
    res.type("text/plain");
    if (error) {
      return res.status(500).send(stderr || error.message);
    }
    return res.send(stdout);
  });
});

app.post("/notes", (req, res) => {
  const { content = "" } = req.body;
  const authorId = req.session.userId;

  db.run("INSERT INTO notes (author_id, content) VALUES (?, ?)", [authorId, content], (err) => {
    if (err) {
      return res.status(500).send("Failed to save note");
    }
    return res.redirect("/");
  });
});

app.listen(PORT, () => {
  console.log(`Vulnerable training app listening on http://localhost:${PORT}`);
});