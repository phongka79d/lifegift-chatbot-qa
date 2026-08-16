import React from 'react';
import { Sparkles } from 'lucide-react';

interface QuickPromptsProps {
  onSelectPrompt: (promptText: string) => void;
}

interface CategoryOption {
  label: string;
  icon: string;
  query: string;
}

const CATEGORIES: CategoryOption[] = [
  { label: 'Cà Phê Specialty', icon: '☕', query: 'Tìm kiếm các loại cà phê specialty Arabica và Robusta kèm giá bán' },
  { label: 'Trà Cổ Thụ', icon: '🍵', query: 'Tư vấn các loại trà Shan Tuyết cổ thụ, trà ướp hoa thơm nhẹ' },
  { label: 'Mật Ong Rừng', icon: '🍯', query: 'Gợi ý mật ong rừng tự nhiên nguyên chất' },
  { label: 'Hạt Dinh Dưỡng', icon: '🌰', query: 'Tìm các loại hạt điều Bình Phước, hạt mắc ca' },
  { label: 'Hoa Quả Sấy', icon: '🥭', query: 'Gợi ý xoài sấy dẻo và mít sấy giòn' },
  { label: 'Hộp Quà Biếu', icon: '🎁', query: 'Tư vấn set quà biếu nông sản cao cấp cho gia đình và đối tác' },
];

const SUGGESTIONS: string[] = [
  '☕ Có cà phê nào dưới 250 nghìn không?',
  '🍵 Tôi thích trà thơm nhẹ thanh nhiệt, giá dưới 200k',
  '⚖️ So sánh Arabica Cầu Đất và Robusta Buôn Ma Thuột',
  '🌿 Lợi ích sức khỏe của trà Shan Tuyết cổ thụ là gì?',
  '📦 Cà phê Arabica Cầu Đất 500g còn hàng trong kho không?',
  '🚚 Tra cứu đơn hàng ORD-20260812-0001 của tôi',
];

export const QuickPrompts: React.FC<QuickPromptsProps> = ({ onSelectPrompt }) => {
  return (
    <div className="quick-prompts-wrapper">
      <div className="quick-prompts-header">
        <Sparkles size={14} style={{ display: 'inline', marginRight: 4 }} />
        Danh mục đặc sản &amp; Câu hỏi gợi ý:
      </div>

      {/* Category Scroll Bar */}
      <div className="category-chips-scroll">
        {CATEGORIES.map((cat, idx) => (
          <button
            key={idx}
            type="button"
            className="category-filter-chip"
            onClick={() => onSelectPrompt(cat.query)}
          >
            <span>{cat.icon}</span>
            <span>{cat.label}</span>
          </button>
        ))}
      </div>

      {/* Detailed Suggestion Chips */}
      <div className="suggested-prompts-grid">
        {SUGGESTIONS.map((item, idx) => {
          // Remove emoji prefix when sending actual prompt text for clean UX
          const textWithoutEmoji = item.replace(/^[^\w\s\u00C0-\u1EF9]+/u, '').trim();
          return (
            <button
              key={idx}
              type="button"
              className="prompt-chip"
              onClick={() => onSelectPrompt(textWithoutEmoji)}
            >
              {item}
            </button>
          );
        })}
      </div>
    </div>
  );
};
