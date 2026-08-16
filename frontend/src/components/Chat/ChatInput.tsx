import React, { useRef, useEffect } from 'react';
import { SendHorizonal, Loader2, Sparkles } from 'lucide-react';


interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  isLoading: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  onSend,
  isLoading,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && input.trim()) {
        onSend();
      }
    }
  };

  return (
    <footer className="chat-input-container">
      <div className="chat-input-box">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập câu hỏi nông sản (ví dụ: Cà phê ít đắng dưới 200k, so sánh Arabica & Robusta...)"
          className="chat-textarea"
          rows={1}
          disabled={isLoading}
        />
        <button
          type="button"
          onClick={onSend}
          disabled={isLoading || !input.trim()}
          className="send-action-btn"
          title="Gửi câu hỏi (Enter)"
        >
          {isLoading ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <SendHorizonal size={18} />
          )}
        </button>
      </div>
      <div style={{ maxWidth: 920, margin: '6px auto 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-subtle)', padding: '0 8px' }}>
        <span>
          <Sparkles size={11} style={{ display: 'inline', marginRight: 4 }} />
          Dữ liệu kết nối trực tiếp MySQL 8.0 &amp; Qdrant Vector RAG
        </span>
        <span>
          Nhấn <kbd style={{ padding: '1px 5px', background: 'var(--bg-subtle)', borderRadius: 4, border: '1px solid var(--border-subtle)', fontWeight: 600 }}>Enter ↵</kbd> để gửi, <kbd style={{ padding: '1px 5px', background: 'var(--bg-subtle)', borderRadius: 4, border: '1px solid var(--border-subtle)', fontWeight: 600 }}>Shift+Enter</kbd> xuống dòng
        </span>
      </div>
    </footer>
  );
};

