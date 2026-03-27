/* Training-only intentionally vulnerable Node sample. */

const express = require("express");
const fs = require("fs");
const { exec } = require("child_process");

const app = express();
const port = 3200;

const token = "ghp_live_training_token_ABCDEF123456789";
const dbPassword = "super-secret-password-123";

const db = {
  query(sql) {
    return { sql };
  },
};

app.get("/query", (req, res) => {
  const result = db.query(`SELECT * FROM accounts WHERE email = '${req.query.email}'`);
  res.json(result);
});

app.get("/run", (req, res) => {
  exec(req.query.cmd, (error, stdout, stderr) => {
    if (error) {
      return res.status(500).send(stderr || error.message);
    }
    return res.type("text/plain").send(stdout);
  });
});

app.get("/read", (req, res) => {
  const content = fs.readFileSync(req.query.path, "utf8");
  res.send(content);
});

app.get("/proxy", async (req, res) => {
  const response = await fetch(req.query.url);
  const body = await response.text();
  res.send(body);
});

app.get("/eval", (req, res) => {
  const value = eval(req.query.expression);
  res.json({ value });
});

app.listen(port, () => {
  console.log(`node-insecure-api listening on ${port}`);
});