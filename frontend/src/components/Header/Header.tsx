import React, { useEffect, useState } from 'react';
import { RotateCcw, Sprout, User } from 'lucide-react';
import { checkHealth } from '../../services/api';
import type { UserAccount } from '../../types';


interface HeaderProps {
  currentUserId: string;
  onUserChange: (userId: string) => void;
  onResetChat: () => void;
}

const USER_ACCOUNTS: UserAccount[] = [
  { id: '', name: 'Khách vãng lai', roleDescription: 'Chưa đăng nhập' },
  { id: '1', name: 'Nguyễn Văn An', roleDescription: 'ID: 1 - Đơn ORD-20260812-0001', sampleOrder: 'ORD-20260812-0001' },
  { id: '2', name: 'Trần Thị Mai', roleDescription: 'ID: 2 - Đơn ORD-20260810-0099', sampleOrder: 'ORD-20260810-0099' },
];

/**
 * Top Application Header with Brand, Health Ping, User Switcher, and Reset Action.
 */
export const Header: React.FC<HeaderProps> = ({
  currentUserId,
  onUserChange,
  onResetChat,
}) => {
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then((data) => {
        if (isMounted) setIsBackendHealthy(data.status === 'ok');
      })
      .catch(() => {
        if (isMounted) setIsBackendHealthy(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-logo-icon" aria-hidden="true">
          <Sprout size={22} />
        </div>
        <div className="brand-info">
          <h1>LifeGift AI Assistant</h1>
          <p>Nông Sản Đặc Sản &amp; Tư Vấn Mua Sắm Chuẩn Xác</p>
        </div>
      </div>

      <div className="header-actions">
        <div className="system-status-indicator" title="Trạng thái hệ thống AI">
          <span
            className={`status-dot ${isBackendHealthy === false ? 'error' : ''}`}
          />
          <span>{isBackendHealthy === false ? 'Mất kết nối BE' : 'RAG & MySQL Online'}</span>
        </div>

        <div className="user-selector-container">
          <User size={15} />
          <select
            id="user-select-dropdown"
            aria-label="Chọn tài khoản người dùng"
            value={currentUserId}
            onChange={(e) => onUserChange(e.target.value)}
            className="user-select-dropdown"
          >
            {USER_ACCOUNTS.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.name} ({acc.roleDescription})
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={onResetChat}
          className="new-chat-btn"
          title="Bắt đầu phiên hội thoại mới"
        >
          <RotateCcw size={14} />
          <span>Hội thoại mới</span>
        </button>
      </div>
    </header>
  );
};
