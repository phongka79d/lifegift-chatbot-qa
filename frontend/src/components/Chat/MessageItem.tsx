import React, { useState } from 'react';
import { Copy, Check, Bot, User } from 'lucide-react';
import type { ChatMessage } from '../../types';

import { MarkdownContent } from './MarkdownContent';
import { ProductCard } from '../Product/ProductCard';

interface MessageItemProps {
  message: ChatMessage;
  onOpenProductDetail: (productId: number) => void;
  onAskAboutProduct: (productName: string) => void;
  onShowToast: (text: string) => void;
}

const INTENT_LABELS: Record<string, string> = {
  PRODUCT_SEARCH: '🔍 Tìm kiếm sản phẩm',
  PRODUCT_DETAIL: '📄 Chi tiết sản phẩm',
  PRODUCT_RECOMMENDATION: '💡 Gợi ý theo khẩu vị',
  PRODUCT_COMPARE: '⚖️ So sánh đặc sản',
  KNOWLEDGE: '🌿 Kiến thức nông sản',
  PRODUCT_REVIEW: '⭐ Đánh giá khách hàng',
  ORDER_STATUS: '🚚 Tra cứu đơn hàng',
  GENERAL: '💬 Trợ lý LifeGift',
};

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onOpenProductDetail,
  onAskAboutProduct,
  onShowToast,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      onShowToast('Đã sao chép nội dung vào bộ nhớ tạm');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      onShowToast('Không thể sao chép nội dung');
    }
  };

  return (
    <div className={`message-item ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-avatar" aria-hidden="true">
        <div className="avatar-badge">
          {isUser ? <User size={18} /> : <Bot size={18} />}
        </div>
      </div>

      <div className="message-content-wrapper">
        <div className="message-header-info">
          <span className="message-author-name">
            {isUser ? 'Bạn' : 'Trợ Lý LifeGift'}
          </span>
          <span className="message-time">{message.timestamp}</span>
          {!isUser && message.intent && (
            <span className="intent-badge">
              {INTENT_LABELS[message.intent] || message.intent}
            </span>
          )}
        </div>

        <div className={`message-bubble ${message.isError ? 'error-bubble' : ''}`}>
          <MarkdownContent content={message.content} />
        </div>

        {/* Product Cards Grid */}
        {message.products && message.products.length > 0 && (
          <div className="product-cards-grid">
            {message.products.map((prod) => (
              <ProductCard
                key={prod.id}
                product={prod}
                onOpenDetail={onOpenProductDetail}
                onAskAboutProduct={onAskAboutProduct}
              />
            ))}
          </div>
        )}

        {/* Action bar for assistant messages */}
        {!isUser && !message.isError && (
          <div className="message-actions-bar">
            <button
              type="button"
              className="action-icon-btn"
              onClick={handleCopy}
              title="Sao chép câu trả lời"
            >
              {copied ? <Check size={14} color="#107c41" /> : <Copy size={14} />}
              <span>{copied ? 'Đã sao chép' : 'Sao chép'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
