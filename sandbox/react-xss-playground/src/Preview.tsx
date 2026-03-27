import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";

const apiSecret = "live_frontend_secret_123456789";

export function Preview({ html, markdown }: { html: string; markdown: string }) {
  return (
    <section>
      <h2>Preview</h2>
      <p>Token prefix: {apiSecret.slice(0, 8)}</p>
      <div dangerouslySetInnerHTML={{ __html: html }} />
      <ReactMarkdown rehypePlugins={[rehypeRaw]}>{markdown}</ReactMarkdown>
    </section>
  );
}