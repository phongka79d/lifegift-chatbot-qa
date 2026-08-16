import React, { useState, useCallback } from 'react';
import { Header } from './components/Header/Header';
import { MessageList } from './components/Chat/MessageList';
import { ChatInput } from './components/Chat/ChatInput';
import { ProductModal } from './components/Product/ProductModal';
import { Toast } from './components/Common/Toast';
import type { ChatMessage } from './types';
import { sendChatMessage } from './services/api';


export const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string>('');
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
  }, []);

  const handleResetChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setInput('');
    showToast('Đã bắt đầu phiên hội thoại mới');
  }, [showToast]);

  const handleSendMessage = useCallback(
    async (textToSend?: string) => {
      const query = (textToSend !== undefined ? textToSend : input).trim();
      if (!query || isLoading) return;

      const now = new Date();
      const timeStr = now.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
      });

      const userMsgId = `user-${Date.now()}`;
      const newUserMessage: ChatMessage = {
        id: userMsgId,
        role: 'user',
        content: query,
        timestamp: timeStr,
      };

      setMessages((prev) => [...prev, newUserMessage]);
      setInput('');
      setIsLoading(true);

      try {
        const response = await sendChatMessage(sessionId, query, currentUserId);
        setSessionId(response.session_id);

        const assistantMsgId = `asst-${Date.now()}`;
        const newAssistantMessage: ChatMessage = {
          id: assistantMsgId,
          role: 'assistant',
          content: response.answer,
          timestamp: new Date().toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
          }),
          products: response.products,
          intent: response.intent,
        };

        setMessages((prev) => [...prev, newAssistantMessage]);
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : 'Đã xảy ra sự cố khi kết nối đến máy chủ.';

        const errorMsgId = `err-${Date.now()}`;
        setMessages((prev) => [
          ...prev,
          {
            id: errorMsgId,
            role: 'assistant',
            content: errorMessage,
            timestamp: new Date().toLocaleTimeString('vi-VN', {
              hour: '2-digit',
              minute: '2-digit',
            }),
            isError: true,
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [input, isLoading, sessionId, currentUserId]
  );

  return (
    <div className="app-layout">
      <Header
        currentUserId={currentUserId}
        onUserChange={setCurrentUserId}
        onResetChat={handleResetChat}
      />

      <MessageList
        messages={messages}
        isLoading={isLoading}
        onOpenProductDetail={setSelectedProductId}
        onSelectPrompt={(prompt) => handleSendMessage(prompt)}
        onShowToast={showToast}
      />

      <ChatInput
        input={input}
        setInput={setInput}
        onSend={() => handleSendMessage()}
        isLoading={isLoading}
      />

      <ProductModal
        productId={selectedProductId}
        onClose={() => setSelectedProductId(null)}
        onAskAboutProduct={(name) => handleSendMessage(`Tư vấn thêm về sản phẩm ${name}`)}
      />

      <Toast
        message={toastMessage}
        onClose={() => setToastMessage(null)}
      />
    </div>
  );
};

export default App;
