import React, { useEffect, useState } from 'react';
import {
  X,
  ShieldCheck,
  MapPin,
  Clock,
  MessageCircle,
} from 'lucide-react';
import type {
  ProductDetailResponse,
  ProductReviewsResponse,
} from '../../types';

import {
  fetchProductDetail,
  fetchProductReviews,
  formatVND,
} from '../../services/api';

interface ProductModalProps {
  productId: number | null;
  onClose: () => void;
  onAskAboutProduct: (productName: string) => void;
}

type TabType = 'overview' | 'taste' | 'story' | 'certs' | 'reviews';

export const ProductModal: React.FC<ProductModalProps> = ({
  productId,
  onClose,
  onAskAboutProduct,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [detail, setDetail] = useState<ProductDetailResponse | null>(null);
  const [reviewsData, setReviewsData] = useState<ProductReviewsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;

    setLoading(true);
    setError(null);
    setActiveTab('overview');

    Promise.all([
      fetchProductDetail(productId),
      fetchProductReviews(productId).catch(() => null),
    ])
      .then(([prodDetail, prodReviews]) => {
        setDetail(prodDetail);
        setReviewsData(prodReviews);
      })
      .catch((err) => {
        setError(err.message || 'Không thể tải thông tin sản phẩm');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [productId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!productId) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <p>{detail?.category_name || 'Nông sản'} · {detail?.brand_name || 'LifeGift'}</p>
            <h2>{detail ? detail.name : 'Chi tiết sản phẩm'}</h2>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} title="Đóng cửa sổ">
            <X size={18} />
          </button>
        </div>

        {/* Tab Selection */}
        <div className="modal-tabs-bar">
          <button
            type="button"
            className={`modal-tab-button ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Tổng quan
          </button>
          <button
            type="button"
            className={`modal-tab-button ${activeTab === 'taste' ? 'active' : ''}`}
            onClick={() => setActiveTab('taste')}
          >
            Hương vị &amp; Cảm quan
          </button>
          <button
            type="button"
            className={`modal-tab-button ${activeTab === 'story' ? 'active' : ''}`}
            onClick={() => setActiveTab('story')}
          >
            Nguồn gốc &amp; Sử dụng
          </button>
          <button
            type="button"
            className={`modal-tab-button ${activeTab === 'certs' ? 'active' : ''}`}
            onClick={() => setActiveTab('certs')}
          >
            Chứng chỉ ({detail?.certificates?.length || 0})
          </button>
          <button
            type="button"
            className={`modal-tab-button ${activeTab === 'reviews' ? 'active' : ''}`}
            onClick={() => setActiveTab('reviews')}
          >
            Đánh giá ({reviewsData?.total_reviews || 0})
          </button>
        </div>

        {/* Modal Content Body */}
        <div className="modal-content-body">
          {loading && (
            <div className="message-bubble is-skeleton">
              <div className="skeleton-box skeleton-text-line medium" />
              <div className="skeleton-box skeleton-text-line long" />
              <div className="skeleton-box skeleton-text-line short" />
            </div>
          )}

          {error && (
            <div style={{ color: 'var(--danger-red)', padding: 24, textAlign: 'center' }}>
              {error}
            </div>
          )}

          {!loading && detail && (
            <>
              {activeTab === 'overview' && (
                <div>
                  <div className="modal-overview">
                    <img
                      src={detail.image_url || 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600'}
                      alt={detail.name}
                    />
                    <div className="modal-overview-copy">
                      <div className="product-card-pricing-row" style={{ marginBottom: 8 }}>
                        <span className="product-effective-price" style={{ fontSize: '1.25rem' }}>
                          {formatVND(detail.effective_price)}
                        </span>
                        {detail.sale_price && (
                          <span className="product-original-price">
                            {formatVND(detail.price)}
                          </span>
                        )}
                      </div>
                      <p className="review-comment" style={{ marginBottom: 8 }}>
                        {detail.description || 'Đặc sản được kiểm soát chất lượng từ gieo trồng đến thu hoạch.'}
                      </p>
                      <div className="modal-section">
                        <p><MapPin size={13} /> Xuất xứ: {detail.origin || 'Việt Nam'}</p>
                        <p><Clock size={13} /> Tồn kho: {detail.available_quantity} sản phẩm</p>
                        {detail.shelf_life && <p>Hạn sử dụng: {detail.shelf_life}</p>}
                        {detail.storage_instructions && <p>Bảo quản: {detail.storage_instructions}</p>}
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn-card-detail modal-ask-btn"
                    onClick={() => {
                      onClose();
                      onAskAboutProduct(detail.name);
                    }}
                  >
                    <MessageCircle size={16} />
                    Hỏi về sản phẩm này
                  </button>
                </div>
              )}

              {activeTab === 'taste' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {detail.taste_profile && (
                    <div className="modal-section">
                      <h4>Hương vị</h4>
                      <p>{detail.taste_profile}</p>
                    </div>
                  )}

                  {detail.ingredients && (
                    <div className="modal-section">
                      <h4>Thành phần</h4>
                      <p>{detail.ingredients}</p>
                    </div>
                  )}

                  {detail.key_benefits && (
                    <div className="modal-section">
                      <h4>Công dụng</h4>
                      <p>{detail.key_benefits}</p>
                    </div>
                  )}

                  {detail.suitable_for && (
                    <div className="modal-section">
                      <h4>Phù hợp với</h4>
                      <p>{detail.suitable_for}</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'story' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {detail.product_story && (
                    <div className="modal-section">
                      <h4>Nguồn gốc</h4>
                      <p>{detail.product_story}</p>
                    </div>
                  )}

                  {detail.usage_instructions && (
                    <div className="modal-section">
                      <h4>Cách dùng</h4>
                      <p>{detail.usage_instructions}</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'certs' && (
                <div>
                  {detail.certificates && detail.certificates.length > 0 ? (
                    detail.certificates.map((c, i) => (
                      <div key={i} className="cert-card-item">
                        <div className="icon"><ShieldCheck color="var(--primary-forest)" size={24} /></div>
                        <div>
                          <div className="name">{c.name} {c.certificate_code ? `(${c.certificate_code})` : ''}</div>
                          <div className="issuer">Cấp bởi: {c.issuer || 'Cơ quan chứng nhận thẩm quyền'}</div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p style={{ fontSize: '0.88rem', color: 'var(--text-subtle)', textAlign: 'center', padding: 20 }}>
                      Chưa có chứng chỉ niêm yết công khai cho sản phẩm này.
                    </p>
                  )}
                </div>
              )}

              {activeTab === 'reviews' && (
                <div>
                  {reviewsData && reviewsData.reviews.length > 0 ? (
                    <>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, padding: '12px 16px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
                        <span style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--primary-forest)' }}>
                          {reviewsData.average_rating.toFixed(1)}/5
                        </span>
                        <div className="review-stars" style={{ fontSize: '1rem' }}>
                          {'★'.repeat(Math.round(reviewsData.average_rating))}
                        </div>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>
                          &bull; {reviewsData.total_reviews} đánh giá đã duyệt
                        </span>
                      </div>
                      {reviewsData.reviews.map((r) => (
                        <div key={r.id} className="review-card-item">
                          <div className="review-header">
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'var(--primary-forest)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 700 }}>
                                {r.user_name.charAt(0).toUpperCase()}
                              </div>
                              <span className="review-author">{r.user_name}</span>
                              {r.is_verified_purchase && (
                                <span style={{ fontSize: '0.68rem', color: 'var(--success-green)', background: 'var(--success-bg)', padding: '1px 6px', borderRadius: 4, fontWeight: 700 }}>
                                  ✓ Đã mua hàng
                                </span>
                              )}
                            </div>
                            <span className="review-stars">{'★'.repeat(r.rating)}</span>
                          </div>
                          <p className="review-comment">{r.comment}</p>
                        </div>
                      ))}
                    </>
                  ) : (
                    <p style={{ fontSize: '0.88rem', color: 'var(--text-subtle)', textAlign: 'center', padding: 20 }}>
                      Chưa có đánh giá nào từ khách hàng cho sản phẩm này.
                    </p>
                  )}
                </div>
              )}

            </>
          )}
        </div>
      </div>
    </div>
  );
};
