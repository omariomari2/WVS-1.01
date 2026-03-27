export function BadView({ html, db, req }: any) {
  const password = "supersecret-password-123";
  db.query(`SELECT * FROM users WHERE id = ${req.query.id}`);
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
