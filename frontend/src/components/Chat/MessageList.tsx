import React, { useEffect, useRef } from 'react';
import { Bot } from 'lucide-react';
import type { ChatMessage } from '../../types';

import { MessageItem } from './MessageItem';
import { QuickPrompts } from './QuickPrompts';

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onOpenProductDetail: (productId: number) => void;
  onSelectPrompt: (promptText: string) => void;
  onShowToast: (text: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  onOpenProductDetail,
  onSelectPrompt,
  onShowToast,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <main className="chat-viewport">
      <div className="messages-list-wrapper">
        {/* Welcome message if no user message has been sent */}
        {messages.length === 0 && (
          <div className="message-item assistant">
            <div className="message-avatar" aria-hidden="true">
              <div className="avatar-badge">
                <Bot size={18} />
              </div>
            </div>
            <div className="message-content-wrapper">
              <div className="message-header-info">
                <span className="message-author-name">Trợ Lý LifeGift</span>
              </div>
              <div className="message-bubble">
                <p>
                  Xin chào! Em là <strong>Trợ lý Nông sản LifeGift</strong>. Em được kết nối trực tiếp với cơ sở dữ liệu tồn kho, giá bán và hệ thống kiểm định chất lượng nông sản Việt Nam.
                </p>
                <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                  <li>Tra cứu giá bán và tồn kho khả dụng thời gian thực.</li>
                  <li>Tư vấn sản phẩm chuẩn theo khẩu vị (thơm nhẹ, ít đắng, thanh nhiệt...).</li>
                  <li>So sánh chi tiết đặc tính, nguồn gốc giữa các dòng đặc sản.</li>
                  <li>Cung cấp kiến thức nông sản sạch, hướng dẫn pha chế và chứng chỉ OCOP/VietGAP.</li>
                  <li>Tra cứu trạng thái vận chuyển và lịch sử đơn hàng của bạn.</li>
                </ul>
              </div>

              {/* Quick Prompts on initial view */}
              <QuickPrompts onSelectPrompt={onSelectPrompt} />
            </div>
          </div>
        )}

        {/* Message Stream */}
        {messages.map((msg) => (
          <MessageItem
            key={msg.id}
            message={msg}
            onOpenProductDetail={onOpenProductDetail}
            onAskAboutProduct={onSelectPrompt}
            onShowToast={onShowToast}
          />
        ))}

        {/* Loading / Skeletal Shimmer Indicator (tasteskill compliant) */}
        {isLoading && (
          <div className="message-item assistant">
            <div className="message-avatar" aria-hidden="true">
              <div className="avatar-badge">
                <Bot size={18} />
              </div>
            </div>
            <div className="message-content-wrapper">
              <div className="message-header-info">
                <span className="message-author-name">Trợ Lý LifeGift</span>
                <span className="message-time">Đang tra cứu dữ liệu...</span>
              </div>
              <div className="message-bubble" style={{ minWidth: 280, padding: 18 }}>
                <div className="skeleton-box skeleton-text-line medium" />
                <div className="skeleton-box skeleton-text-line long" />
                <div className="skeleton-box skeleton-text-line short" style={{ marginBottom: 0 }} />
              </div>
              <div className="skeleton-cards-grid">
                <div className="skeleton-box skeleton-card" />
                <div className="skeleton-box skeleton-card" />
              </div>
            </div>
          </div>
        )}


        <div ref={bottomRef} style={{ height: 1 }} />
      </div>
    </main>
  );
};
