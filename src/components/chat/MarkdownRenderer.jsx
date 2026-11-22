import React, { memo, useMemo, useState } from 'react';
import { Check, Copy } from 'lucide-react';

/* ---------- Streaming repair ---------- */

// Hides syntax that is still arriving so raw markers never flash on screen.
function healTail(line) {
  const marker = line.match(/^\s*(?:[-*+]|\d+[.)])\s+/)?.[0] || '';
  let body = line.slice(marker.length);

  body = body.replace(/\[([^\]]*)\]\([^)]*$/, '$1');
  body = body.replace(/\[([^\]]*)$/, (_, inner) => (/^\d{0,3}(?:[,\s\d]*|†.*)$/.test(inner) ? '' : inner));

  const ticks = (body.match(/`/g) || []).length;
  if (ticks % 2 === 1) body += '`';

  body = body.replace(/\*+$/, '');
  const outsideCode = () => body.replace(/`[^`]*`/g, '');
  if (((outsideCode().match(/\*\*/g) || []).length) % 2 === 1) body += '**';
  if (((outsideCode().replace(/\*\*/g, '').match(/\*/g) || []).length) % 2 === 1) body += '*';

  return marker + body;
}

function prepareStreaming(source) {
  let text = source
    .replace(/<think>[\s\S]*?<\/think>/g, '')
    .replace(/<think>[\s\S]*$/, '')
    .replace(/\[(\d+)†[^\]]*\]/g, '[$1]');

  const lines = text.split('\n');
  const fences = lines.filter((l) => /^\s{0,3}(```|~~~)/.test(l)).length;
  if (fences % 2 === 0) {
    const last = lines.length - 1;
    if (/^\s*(?:`{1,2}|#{1,6}|[-*+]|\d+[.)]?)\s*$/.test(lines[last])) lines[last] = '';
    else lines[last] = healTail(lines[last]);
    text = lines.join('\n');
  }
  return text;
}

/* ---------- Block parser ---------- */

const FENCE = /^\s{0,3}(`{3,}|~{3,})\s*([\w+#.-]*)\s*$/;
const HEADING = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/;
const RULE = /^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/;
const LIST_ITEM = /^(\s*)([-*+]|\d{1,4}[.)])\s+(.*)$/;
const QUOTE = /^\s{0,3}>\s?(.*)$/;
const TABLE_SEP = /^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$/;

const isTableRow = (line) => line.includes('|') && line.trim().length > 1;

function splitRow(line) {
  let row = line.trim();
  if (row.startsWith('|')) row = row.slice(1);
  if (row.endsWith('|') && !row.endsWith('\\|')) row = row.slice(0, -1);
  return row.split(/(?<!\\)\|/).map((cell) => cell.trim().replace(/\\\|/g, '|'));
}

const indentOf = (space) => space.replace(/\t/g, '    ').length;

function parseList(lines, startIndex) {
  const first = lines[startIndex].match(LIST_ITEM);
  const makeList = (marker, indent) => ({
    ordered: /\d/.test(marker),
    start: /\d/.test(marker) ? parseInt(marker, 10) : 1,
    indent,
    items: [],
  });
  const root = makeList(first[2], indentOf(first[1]));
  const stack = [root];
  let i = startIndex;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      let next = i + 1;
      while (next < lines.length && !lines[next].trim()) next += 1;
      if (next < lines.length && (LIST_ITEM.test(lines[next]) || /^\s{2,}\S/.test(lines[next]))) {
        i = next;
        continue;
      }
      break;
    }

    const item = line.match(LIST_ITEM);
    if (item && !RULE.test(line)) {
      const indent = indentOf(item[1]);
      const ordered = /\d/.test(item[2]);
      while (stack.length > 1 && indent < stack[stack.length - 1].indent) stack.pop();

      let current = stack[stack.length - 1];
      if (indent >= current.indent + 2 && current.items.length) {
        const nested = makeList(item[2], indent);
        current.items[current.items.length - 1].children.push(nested);
        stack.push(nested);
        current = nested;
      } else if (current.ordered !== ordered) {
        if (stack.length === 1) break;
        stack.pop();
        const parent = stack[stack.length - 1];
        const sibling = makeList(item[2], indent);
        parent.items[parent.items.length - 1].children.push(sibling);
        stack.push(sibling);
        current = sibling;
      }
      current.items.push({ text: item[3], children: [] });
      i += 1;
      continue;
    }

    if (/^\s{2,}\S/.test(line)) {
      const current = stack[stack.length - 1];
      const last = current.items[current.items.length - 1];
      last.text += `\n${line.trim()}`;
      i += 1;
      continue;
    }
    break;
  }

  return { list: root, next: i };
}

function parseBlocks(source, streaming) {
  const lines = source.replace(/\r\n?/g, '\n').split('\n');
  const blocks = [];
  let i = 0;

  const startsBlock = (line, nextLine, isLast) => (
    FENCE.test(line) || HEADING.test(line) || RULE.test(line) || QUOTE.test(line) || LIST_ITEM.test(line)
    || isTableStart(line, nextLine, isLast)
  );

  function isTableStart(line, nextLine, isLast) {
    if (!isTableRow(line)) return false;
    if (nextLine !== undefined && TABLE_SEP.test(nextLine) && nextLine.includes('-')) return true;
    if (!streaming || !line.trim().startsWith('|')) return false;
    return isLast || (nextLine !== undefined && /^[\s|:-]*$/.test(nextLine));
  }

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i += 1; continue; }

    const fence = line.match(FENCE);
    if (fence) {
      const marker = fence[1];
      const body = [];
      let j = i + 1;
      let closed = false;
      while (j < lines.length) {
        const candidate = lines[j].trim();
        if (candidate.startsWith(marker) && /^[`~]+$/.test(candidate)) { closed = true; break; }
        body.push(lines[j]);
        j += 1;
      }
      blocks.push({ type: 'code', language: fence[2], code: body.join('\n'), open: !closed, raw: lines.slice(i, j + 1).join('\n') });
      i = j + 1;
      continue;
    }

    const heading = line.match(HEADING);
    if (heading) {
      blocks.push({ type: 'heading', level: Math.min(heading[1].length, 4), text: heading[2], raw: line });
      i += 1;
      continue;
    }

    if (RULE.test(line)) {
      blocks.push({ type: 'rule', raw: line });
      i += 1;
      continue;
    }

    if (isTableStart(line, lines[i + 1], i === lines.length - 1)) {
      const header = splitRow(line);
      const separator = lines[i + 1];
      const hasSep = separator !== undefined && /^[\s|:-]*$/.test(separator);
      const align = hasSep
        ? splitRow(separator).map((c) => (c.startsWith(':') && c.endsWith(':') ? 'center' : c.endsWith(':') ? 'right' : 'left'))
        : [];
      let j = hasSep ? i + 2 : i + 1;
      const rows = [];
      while (j < lines.length && lines[j].trim() && isTableRow(lines[j])) {
        const cells = splitRow(lines[j]);
        rows.push(header.map((_, c) => cells[c] ?? ''));
        j += 1;
      }
      blocks.push({ type: 'table', header, align, rows, raw: lines.slice(i, j).join('\n') });
      i = j;
      continue;
    }

    if (QUOTE.test(line)) {
      const body = [];
      let j = i;
      while (j < lines.length && QUOTE.test(lines[j])) {
        body.push(lines[j].match(QUOTE)[1]);
        j += 1;
      }
      blocks.push({ type: 'quote', blocks: parseBlocks(body.join('\n'), streaming), raw: lines.slice(i, j).join('\n') });
      i = j;
      continue;
    }

    if (LIST_ITEM.test(line)) {
      const { list, next } = parseList(lines, i);
      blocks.push({ type: 'list', list, raw: lines.slice(i, next).join('\n') });
      i = next > i ? next : i + 1;
      continue;
    }

    const paragraph = [line.trim()];
    let j = i + 1;
    while (j < lines.length && lines[j].trim() && !startsBlock(lines[j], lines[j + 1], j === lines.length - 1)) {
      paragraph.push(lines[j].trim());
      j += 1;
    }
    blocks.push({ type: 'paragraph', text: paragraph.join('\n'), raw: lines.slice(i, j).join('\n') });
    i = j;
  }

  return blocks;
}

/* ---------- Inline parser ---------- */

function safeHref(url) {
  try {
    const parsed = new URL(url);
    return ['http:', 'https:', 'mailto:'].includes(parsed.protocol) ? parsed.href : null;
  } catch {
    return null;
  }
}

function CitationChip({ n, context }) {
  const source = context.sources?.find((s) => Number(s.ref) === n);
  if (!source) {
    return <span className="cm-cite cm-cite--idle" aria-label={`Citation ${n}`}>{n}</span>;
  }
  return (
    <button
      type="button"
      className="cm-cite"
      title={source.title}
      aria-label={`Open source ${n}: ${source.title}`}
      onClick={() => context.onOpenSource?.(source)}
    >
      {n}
    </button>
  );
}

function renderInline(text, context, keyPrefix = 'i') {
  const nodes = [];
  let plain = '';
  let i = 0;
  let key = 0;

  const flush = () => {
    if (!plain) return;
    const parts = plain.split('\n');
    parts.forEach((part, index) => {
      if (index > 0) nodes.push(<br key={`${keyPrefix}-br-${key++}`} />);
      if (part) nodes.push(part);
    });
    plain = '';
  };
  const push = (node) => { flush(); nodes.push(node); };
  const nextKey = () => `${keyPrefix}-${key++}`;

  while (i < text.length) {
    const char = text[i];
    const rest = text.slice(i);

    if (char === '\\' && /[\\`*_[\]()#+\-.!|~]/.test(text[i + 1] || '')) {
      plain += text[i + 1];
      i += 2;
      continue;
    }

    if (char === '`') {
      const end = text.indexOf('`', i + 1);
      if (end > i + 1) {
        push(<code key={nextKey()} className="cm-inline-code">{text.slice(i + 1, end)}</code>);
        i = end + 1;
        continue;
      }
    }

    if (char === '*' || char === '_') {
      const previous = text[i - 1] || ' ';
      const wordInside = char === '_' && /\w/.test(previous);
      if (!wordInside) {
        const pair = char === '*'
          ? rest.match(/^\*\*(?=\S)([\s\S]*?\S)\*\*/)
          : rest.match(/^__(?=\S)([\s\S]*?\S)__(?!\w)/);
        if (pair) {
          const k = nextKey();
          push(<strong key={k}>{renderInline(pair[1], context, k)}</strong>);
          i += pair[0].length;
          continue;
        }
        const single = char === '*'
          ? rest.match(/^\*(?=[^\s*])([^*\n]*[^\s*])\*(?!\*)/)
          : rest.match(/^_(?=[^\s_])([^_\n]*[^\s_])_(?!\w)/);
        if (single) {
          const k = nextKey();
          push(<em key={k}>{renderInline(single[1], context, k)}</em>);
          i += single[0].length;
          continue;
        }
      }
    }

    if (char === '~') {
      const strike = rest.match(/^~~(?=\S)([\s\S]*?\S)~~/);
      if (strike) {
        const k = nextKey();
        push(<del key={k}>{renderInline(strike[1], context, k)}</del>);
        i += strike[0].length;
        continue;
      }
    }

    if (char === '[') {
      const citation = rest.match(/^\[(\d{1,3}(?:\s*,\s*\d{1,3})*)\](?!\()/);
      if (citation) {
        flush();
        citation[1].split(',').forEach((value) => {
          nodes.push(<CitationChip key={nextKey()} n={Number(value.trim())} context={context} />);
        });
        i += citation[0].length;
        continue;
      }
      const link = rest.match(/^\[([^\]]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/);
      if (link) {
        const href = safeHref(link[2]);
        if (href) {
          const k = nextKey();
          push(<a key={k} href={href} target="_blank" rel="noopener noreferrer">{renderInline(link[1], context, k)}</a>);
        } else {
          plain += link[1];
        }
        i += link[0].length;
        continue;
      }
    }

    if ((char === 'h' || char === 'H') && !/\w/.test(text[i - 1] || ' ')) {
      const url = rest.match(/^https?:\/\/[^\s<>()]+/i);
      if (url) {
        const clean = url[0].replace(/[.,;:!?'"]+$/, '');
        const href = safeHref(clean);
        if (href) {
          push(<a key={nextKey()} href={href} target="_blank" rel="noopener noreferrer">{clean}</a>);
          i += clean.length;
          continue;
        }
      }
    }

    plain += char;
    i += 1;
  }

  flush();
  return nodes;
}

/* ---------- Block rendering ---------- */

const Caret = () => <span className="cm-caret" aria-hidden="true" />;

function CodeBlock({ code, language, caret }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="cm-code">
      <div className="cm-code__bar">
        <span>{language || 'code'}</span>
        <button type="button" onClick={handleCopy} aria-label="Copy code">
          {copied ? <Check size={13} /> : <Copy size={13} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre><code>{code}{caret && <Caret />}</code></pre>
    </div>
  );
}

function ListBlock({ list, context, caret }) {
  const Tag = list.ordered ? 'ol' : 'ul';
  const lastItem = list.items.length - 1;
  return (
    <Tag start={list.ordered && list.start !== 1 ? list.start : undefined}>
      {list.items.map((item, index) => {
        const isLast = index === lastItem;
        const hasChildren = item.children.length > 0;
        return (
          <li key={index}>
            {renderInline(item.text, context, `li-${index}`)}
            {caret && isLast && !hasChildren && <Caret />}
            {item.children.map((child, childIndex) => (
              <ListBlock
                key={childIndex}
                list={child}
                context={context}
                caret={caret && isLast && childIndex === item.children.length - 1}
              />
            ))}
          </li>
        );
      })}
    </Tag>
  );
}

function TableBlock({ block, context, caret }) {
  const lastRow = block.rows.length - 1;
  const lastCell = block.header.length - 1;
  return (
    <div className="cm-table" role="region" aria-label="Table" tabIndex={0}>
      <table>
        <thead>
          <tr>
            {block.header.map((cell, c) => (
              <th key={c} style={{ textAlign: block.align[c] || 'left' }}>
                {renderInline(cell, context, `th-${c}`)}
                {caret && lastRow < 0 && c === lastCell && <Caret />}
              </th>
            ))}
          </tr>
        </thead>
        {block.rows.length > 0 && (
          <tbody>
            {block.rows.map((row, r) => (
              <tr key={r}>
                {row.map((cell, c) => (
                  <td key={c} style={{ textAlign: block.align[c] || 'left' }}>
                    {renderInline(cell, context, `td-${r}-${c}`)}
                    {caret && r === lastRow && c === lastCell && <Caret />}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        )}
      </table>
    </div>
  );
}

const Block = memo(function Block({ block, context, caret }) {
  switch (block.type) {
    case 'code':
      return <CodeBlock code={block.code} language={block.language} caret={caret} />;
    case 'heading': {
      const Tag = `h${block.level}`;
      return <Tag>{renderInline(block.text, context)}{caret && <Caret />}</Tag>;
    }
    case 'rule':
      return <hr />;
    case 'table':
      return <TableBlock block={block} context={context} caret={caret} />;
    case 'quote':
      return (
        <blockquote>
          {block.blocks.map((inner, index) => (
            <Block key={index} block={inner} context={context} caret={caret && index === block.blocks.length - 1} />
          ))}
        </blockquote>
      );
    case 'list':
      return <ListBlock list={block.list} context={context} caret={caret} />;
    default:
      return <p>{renderInline(block.text, context)}{caret && <Caret />}</p>;
  }
}, (a, b) => a.block.raw === b.block.raw && a.caret === b.caret && a.context === b.context);

export default function MarkdownRenderer({ content, streaming = false, sources, onOpenSource }) {
  const context = useMemo(() => ({ sources, onOpenSource }), [sources, onOpenSource]);
  const blocks = useMemo(() => {
    if (!content) return [];
    return parseBlocks(streaming ? prepareStreaming(content) : content, streaming);
  }, [content, streaming]);

  if (!blocks.length) return streaming ? <div className="cm-md"><p><Caret /></p></div> : null;

  return (
    <div className="cm-md">
      {blocks.map((block, index) => (
        <Block
          key={index}
          block={block}
          context={context}
          caret={streaming && index === blocks.length - 1}
        />
      ))}
    </div>
  );
}
