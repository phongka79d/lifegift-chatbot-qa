import React, { useMemo } from 'react';

interface MarkdownContentProps {
  content: string;
}

/**
 * Clean & safe markdown parser for structured chatbot outputs (tables, lists, quotes, text).
 */
export const MarkdownContent: React.FC<MarkdownContentProps> = ({ content }) => {
  const htmlContent = useMemo(() => {
    if (!content) return '';

    // Step 1: Escape HTML characters
    let raw = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Step 2: Code blocks (inline `code`)
    raw = raw.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Step 3: Bold & Italic
    raw = raw.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
    raw = raw.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    raw = raw.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Step 4: Parse Tables
    const lines = raw.split('\n');
    const processedLines: string[] = [];
    let inTable = false;
    let tableBuffer: string[] = [];

    const flushTable = () => {
      if (tableBuffer.length > 0) {
        let tableHtml = '<div class="table-responsive"><table>';
        let hasHeader = false;

        tableBuffer.forEach((rowLine, index) => {
          const cells = rowLine
            .split('|')
            .map((c) => c.trim())
            .filter((_, i, arr) => i > 0 && i < arr.length);


          if (cells.length > 0) {
            // Check if separator line
            if (cells.every((c) => /^:?-+:?$/.test(c))) {
              hasHeader = true;
              return;
            }

            const tag = index === 0 && !hasHeader ? 'th' : inTable && hasHeader ? 'td' : 'td';
            const cellHtml = cells.map((cell) => `<${tag}>${cell}</${tag}>`).join('');
            tableHtml += `<tr>${cellHtml}</tr>`;
          }
        });

        tableHtml += '</table></div>';
        processedLines.push(tableHtml);
        tableBuffer = [];
      }
      inTable = false;
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        inTable = true;
        tableBuffer.push(trimmed);
      } else {
        if (inTable) {
          flushTable();
        }

        // Blockquotes
        if (trimmed.startsWith('&gt; ')) {
          processedLines.push(`<blockquote>${trimmed.substring(5)}</blockquote>`);
        }
        // Bullet lists
        else if (/^[-*]\s+/.test(trimmed)) {
          processedLines.push(`<li>${trimmed.replace(/^[-*]\s+/, '')}</li>`);
        }
        // Numbered lists
        else if (/^\d+\.\s+/.test(trimmed)) {
          processedLines.push(`<li>${trimmed.replace(/^\d+\.\s+/, '')}</li>`);
        }
        // Empty lines
        else if (trimmed === '') {
          processedLines.push('<br/>');
        }
        // Normal paragraphs
        else {
          processedLines.push(`<p>${trimmed}</p>`);
        }
      }
    }

    if (inTable) {
      flushTable();
    }

    let finalHtml = processedLines.join('');
    // Wrap adjacent <li> in <ul>
    finalHtml = finalHtml.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');
    // Remove consecutive <br/>
    finalHtml = finalHtml.replace(/(<br\/>){2,}/g, '<br/>');

    return finalHtml;
  }, [content]);

  return (
    <div
      className="markdown-body"
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
};
