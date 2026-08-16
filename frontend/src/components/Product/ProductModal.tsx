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
            <p>{detail?.category_name || 'Đặc Sản Nông Sản'} &bull; {detail?.brand_name || 'LifeGift'}</p>
            <h2>{detail ? detail.name : 'Chi Tiết Sản Phẩm'}</h2>
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
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <div className="typing-shimmer-indicator">
                <span></span><span></span><span></span>
              </div>
              <p style={{ marginTop: 12, color: 'var(--text-subtle)', fontSize: '0.85rem' }}>
                Đang tải thông tin chi tiết từ hệ sinh thái LifeGift...
              </p>
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
                  <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 20 }}>
                    <img
                      src={detail.image_url || 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600'}
                      alt={detail.name}
                      style={{ width: 140, height: 140, objectFit: 'cover', borderRadius: 12, border: '1px solid var(--border-light)' }}
                    />
                    <div style={{ flex: 1, minWidth: 240 }}>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 8 }}>
                        <span style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary-forest)' }}>
                          {formatVND(detail.effective_price)}
                        </span>
                        {detail.sale_price && (
                          <span style={{ fontSize: '0.9rem', color: 'var(--text-subtle)', textDecoration: 'line-through' }}>
                            {formatVND(detail.price)}
                          </span>
                        )}
                      </div>

                      <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                        {detail.description || 'Đặc sản nông nghiệp sạch được kiểm soát chất lượng từ khâu gieo trồng đến thu hoạch.'}
                      </p>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: '0.8rem', color: 'var(--text-subtle)' }}>
                        <div><MapPin size={13} style={{ display: 'inline', marginRight: 4 }} /> Xuất xứ: <strong style={{ color: 'var(--text-main)' }}>{detail.origin || 'Việt Nam'}</strong></div>
                        <div><Clock size={13} style={{ display: 'inline', marginRight: 4 }} /> Tồn kho khả dụng: <strong style={{ color: 'var(--success-green)' }}>{detail.available_quantity} sản phẩm</strong></div>
                        {detail.shelf_life && <div>Hạn sử dụng: {detail.shelf_life}</div>}
                        {detail.storage_instructions && <div>Bảo quản: {detail.storage_instructions}</div>}
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn-card-detail"
                    style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, width: '100%' }}
                    onClick={() => {
                      onClose();
                      onAskAboutProduct(detail.name);
                    }}
                  >
                    <MessageCircle size={16} />
                    <span>Hỏi trợ lý về sản phẩm này</span>
                  </button>
                </div>
              )}

              {activeTab === 'taste' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {detail.taste_profile && (
                    <div>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--primary-forest)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>
                        Hồ sơ hương vị (Taste Profile)
                      </h4>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.6 }}>{detail.taste_profile}</p>
                    </div>
                  )}

                  {detail.ingredients && (
                    <div>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--primary-forest)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>
                        Thành phần tự nhiên
                      </h4>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.6 }}>{detail.ingredients}</p>
                    </div>
                  )}

                  {detail.key_benefits && (
                    <div>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--primary-forest)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>
                        Lợi ích &amp; Công dụng
                      </h4>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.6 }}>{detail.key_benefits}</p>
                    </div>
                  )}

                  {detail.suitable_for && (
                    <div>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--primary-forest)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>
                        Đối tượng phù hợp
                      </h4>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.6 }}>{detail.suitable_for}</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'story' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {detail.product_story && (
                    <div>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--primary-forest)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>
                        Câu chuyện nguồn gốc &amp; Vùng đất
                      </h4>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.6, fontStyle: 'italic' }}>
                        "{detail.product_story}"
                      </p>
                    </div>
                  )}

                  {detail.usage_instructions && (
                    <div>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--primary-forest)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>
                        Hướng dẫn sử dụng &amp; Pha chế
                      </h4>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.6 }}>{detail.usage_instructions}</p>
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
                          &bull; {reviewsData.total_reviews} đánh giá từ người mua đã xác thực
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
