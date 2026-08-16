import React, { useState } from 'react';
import { MapPin, MessageSquarePlus, Sparkles } from 'lucide-react';
import type { ProductCard as ProductCardType } from '../../types';

import { formatVND } from '../../services/api';

interface ProductCardProps {
  product: ProductCardType;
  onOpenDetail: (productId: number) => void;
  onAskAboutProduct: (productName: string) => void;
}

const FALLBACK_IMAGE = 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600&auto=format&fit=crop&q=80';

/**
 * Enhanced Product Card displaying pricing, stock, origin, and quick actions.
 */
export const ProductCard: React.FC<ProductCardProps> = ({
  product,
  onOpenDetail,
  onAskAboutProduct,
}) => {
  const [imgSrc, setImgSrc] = useState(product.image_url || FALLBACK_IMAGE);

  const discountPercent =
    product.sale_price && product.price > product.sale_price
      ? Math.round(((product.price - product.sale_price) / product.price) * 100)
      : null;

  return (
    <div className="product-card">
      <div className="product-card-img-container">
        <img
          src={imgSrc}
          alt={product.name}
          className="product-card-img"
          loading="lazy"
          onError={() => setImgSrc(FALLBACK_IMAGE)}
        />
        {discountPercent !== null && (
          <span className="badge-discount">-{discountPercent}%</span>
        )}
        <span
          className={`badge-stock ${product.is_available ? 'in-stock' : 'out-stock'}`}
        >
          {product.is_available
            ? `Còn ${product.available_quantity} sp`
            : 'Hết hàng'}
        </span>
      </div>

      <div className="product-card-body">
        <div className="product-card-origin">
          <MapPin size={12} style={{ display: 'inline', marginRight: 3 }} />
          {product.origin || 'Việt Nam'}
        </div>

        <h3 className="product-card-title" title={product.name}>
          {product.name}
        </h3>

        {product.reason && (
          <div className="product-card-reason">
            <Sparkles size={12} style={{ display: 'inline', marginRight: 4 }} />
            {product.reason}
          </div>
        )}

        <div className="product-card-pricing-row">
          <span className="product-effective-price">
            {formatVND(product.effective_price)}
          </span>
          {product.sale_price && (
            <span className="product-original-price">
              {formatVND(product.price)}
            </span>
          )}
        </div>

        <div className="product-card-actions">
          <button
            type="button"
            className="btn-card-detail"
            onClick={() => onOpenDetail(product.id)}
          >
            Chi tiết &amp; Chứng chỉ
          </button>
          <button
            type="button"
            className="btn-card-ask"
            title={`Hỏi chi tiết về ${product.name}`}
            onClick={() => onAskAboutProduct(product.name)}
          >
            <MessageSquarePlus size={15} />
          </button>
        </div>
      </div>
    </div>
  );
};
