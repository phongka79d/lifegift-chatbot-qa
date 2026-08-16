import React, { useRef, useEffect } from 'react';
import { SendHorizonal, Loader2 } from 'lucide-react';


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
          placeholder="Hỏi về cà phê, trà, hạt, giá..."
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
      <p className="input-hint">Enter để gửi · Shift+Enter xuống dòng</p>
    </footer>
  );
};

