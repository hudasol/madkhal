import type { ReactNode } from "react";

// A small renderer for the project's own Markdown documents (headings, paragraphs, lists,
// tables, inline code, bold and links). The documents are part of this repository; no
// external content is rendered.

function inline(text: string, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("`")) out.push(<code key={`${key}-${i}`}>{tok.slice(1, -1)}</code>);
    else if (tok.startsWith("**"))
      out.push(<strong key={`${key}-${i}`}>{tok.slice(2, -2)}</strong>);
    else {
      const mm = /\[([^\]]+)\]\(([^)]+)\)/.exec(tok);
      out.push(mm ? <span key={`${key}-${i}`}>{mm[1]}</span> : tok);
    }
    last = m.index + tok.length;
    i += 1;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text, headingOffset = 1 }: { text: string; headingOffset?: number }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let k = 0;
  while (i < lines.length) {
    const line = lines[i]!;
    if (line.startsWith("```")) {
      const buf: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i]!.startsWith("```")) buf.push(lines[i++]!);
      i += 1;
      blocks.push(
        <pre key={k++} className="code">
          {buf.join("\n")}
        </pre>,
      );
      continue;
    }
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) {
      const level = Math.min(6, h[1]!.length + headingOffset);
      const Tag = `h${level}` as "h2";
      blocks.push(<Tag key={k++}>{inline(h[2]!, `h${k}`)}</Tag>);
      i += 1;
      continue;
    }
    if (line.startsWith("|")) {
      const rows: string[][] = [];
      while (i < lines.length && lines[i]!.startsWith("|")) {
        const cells = lines[i]!.split("|")
          .slice(1, -1)
          .map((c) => c.trim());
        if (!cells.every((c) => /^-+$/.test(c))) rows.push(cells);
        i += 1;
      }
      const [head, ...body] = rows;
      blocks.push(
        <div className="table-wrap" key={k++}>
          <table>
            <thead>
              <tr>
                {(head ?? []).map((c, j) => (
                  <th scope="col" key={j}>
                    {inline(c, `th${k}${j}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((r, ri) => (
                <tr key={ri}>
                  {r.map((c, j) => (
                    <td key={j}>{inline(c, `td${k}${ri}${j}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }
    if (/^\s*([*-]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const items: string[] = [];
      while (
        i < lines.length &&
        lines[i]!.trim() !== "" &&
        !lines[i]!.startsWith("#") &&
        !lines[i]!.startsWith("|")
      ) {
        const l = lines[i]!;
        if (/^\s*([*-]|\d+\.)\s+/.test(l)) items.push(l.replace(/^\s*([*-]|\d+\.)\s+/, ""));
        else items[items.length - 1] = `${items[items.length - 1] ?? ""} ${l.trim()}`;
        i += 1;
      }
      const List = ordered ? "ol" : "ul";
      blocks.push(
        <List key={k++}>
          {items.map((it, j) => (
            <li key={j}>{inline(it, `li${k}${j}`)}</li>
          ))}
        </List>,
      );
      continue;
    }
    if (line.trim() === "") {
      i += 1;
      continue;
    }
    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i]!.trim() !== "" &&
      !/^(#{1,4})\s/.test(lines[i]!) &&
      !lines[i]!.startsWith("|") &&
      !lines[i]!.startsWith("```") &&
      !/^\s*([*-]|\d+\.)\s+/.test(lines[i]!)
    ) {
      para.push(lines[i]!.trim());
      i += 1;
    }
    blocks.push(<p key={k++}>{inline(para.join(" "), `p${k}`)}</p>);
  }
  return <div className="markdown">{blocks}</div>;
}
