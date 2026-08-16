import React, { useEffect, useRef } from 'react';
import { Bot } from 'lucide-react';
import type { ChatMessage } from '../../types';

import { MessageItem } from './MessageItem';
import { QuickPrompts } from './QuickPrompts';
import { ProductRail } from '../Product/ProductRail';

/** Card skeletons only when the last user turn looks like a catalog retrieve. */
function looksLikeProductRetrieval(text?: string): boolean {
  if (!text) return false;
  const t = text.toLowerCase();
  const educational = /(cách |loi ich|lợi ích|hướng dẫn|bảo quản|nhận biết|tiêu chuẩn|vietgap)/i.test(t);
  const catalog =
    /(sản phẩm|san pham|review|đánh giá|danh gia|tìm|tim |gợi ý|goi y|so sánh|so sanh|giá |gia |mua |còn hàng|cà phê|ca phe|trà|chè|hạt|gạo|quà|đặc sản|nông sản|sao|macca|arabica|robusta)/i.test(
      t
    );
  if (!catalog) return false;
  if (educational && !/(sản phẩm|san pham|tìm|tim |gợi ý|mua |giá |review|đánh giá)/i.test(t)) {
    return false;
  }
  return true;
}

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
  const lastUserText = [...messages].reverse().find((m) => m.role === 'user')?.content;
  const showProductSkeleton = isLoading && looksLikeProductRetrieval(lastUserText);

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
                <span className="message-author-name">LifeGift</span>
              </div>
              <div className="message-bubble">
                <p>
                  Xin chào. Tôi tư vấn nông sản LifeGift theo giá, tồn kho và chứng chỉ đang có.
                </p>
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
                <span className="message-author-name">LifeGift</span>
                <span className="message-time">Đang tìm...</span>
              </div>
              <div className="message-bubble is-skeleton">
                <div className="skeleton-box skeleton-text-line medium" />
                <div className="skeleton-box skeleton-text-line long" />
                <div className="skeleton-box skeleton-text-line short" />
              </div>
              {showProductSkeleton && (
                <ProductRail>
                  <div className="skeleton-box skeleton-card" role="listitem" />
                  <div className="skeleton-box skeleton-card" role="listitem" />
                  <div className="skeleton-box skeleton-card" role="listitem" />
                </ProductRail>
              )}
            </div>
          </div>
        )}


        <div ref={bottomRef} style={{ height: 1 }} />
      </div>
    </main>
  );
};
