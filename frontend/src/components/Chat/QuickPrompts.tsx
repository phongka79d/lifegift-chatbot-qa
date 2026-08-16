import React from 'react';

interface QuickPromptsProps {
  onSelectPrompt: (promptText: string) => void;
}

interface CategoryOption {
  label: string;
  query: string;
}

const CATEGORIES: CategoryOption[] = [
  { label: 'Cà phê /kg', query: 'Có cà phê nào dưới 200.000 đồng/kg không?' },
  { label: 'Trà /kg', query: 'Có trà nào dưới 200.000 đồng/kg không?' },
  { label: 'Hạt /kg', query: 'Có hạt nào dưới 200.000 đồng/kg không?' },
  { label: 'Đắk Lắk', query: 'Ở Đắk Lắk có những sản phẩm gì?' },
  { label: 'Pha phin', query: 'Tôi cần cà phê phù hợp để pha phin.' },
  { label: 'Hạt mắc ca', query: 'Tôi muốn biết thông tin về hạt mắc ca.' },
];

const SUGGESTIONS: string[] = [
  'Có cà phê nào dưới 150k/kg không?',
  'Tìm các loại trà từ Thái Nguyên.',
  'Hạt nào được cung cấp từ Bình Phước?',
  'Tôi muốn so sánh các loại cà phê dưới 200k.',
  'Loại trà nào phù hợp để pha uống hằng ngày?',
  'Cà phê Robusta nhân giá bao nhiêu?',
];

export const QuickPrompts: React.FC<QuickPromptsProps> = ({ onSelectPrompt }) => {
  return (
    <div className="quick-prompts-wrapper">
      <p className="quick-prompts-header">Gợi ý câu hỏi</p>

      <div className="category-chips-scroll">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.label}
            type="button"
            className="category-filter-chip"
            onClick={() => onSelectPrompt(cat.query)}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Detailed Suggestion Chips */}
      <div className="suggested-prompts-grid">
        {SUGGESTIONS.map((item, idx) => (
          <button
            key={idx}
            type="button"
            className="prompt-chip"
            onClick={() => onSelectPrompt(item)}
          >
            {item}
          </button>
        ))}
      </div>
    </div>
  );
};
