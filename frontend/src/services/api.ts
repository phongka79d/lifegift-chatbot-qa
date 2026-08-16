/**
 * LifeGift API Service Layer
 */

import type {
  ChatResponse,
  HealthStatus,
  ProductDetailResponse,
  ProductReviewsResponse,
} from '../types';


const API_BASE = '/api';

/**
 * Check backend service health
 */
export async function checkHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error('Không thể kết nối đến máy chủ backend');
  }
  return res.json();
}

/**
 * Send chat message to backend
 */
export async function sendChatMessage(
  sessionId: number | null,
  message: string,
  userId?: string
): Promise<ChatResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (userId && userId.trim() !== '') {
    headers['X-User-Id'] = userId;
  }

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      session_id: sessionId,
      message,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Lỗi hệ thống (${res.status}). Vui lòng thử lại!`
    );
  }

  return res.json();
}

/**
 * Fetch full product detail with certificates
 */
export async function fetchProductDetail(
  productId: number
): Promise<ProductDetailResponse> {
  const res = await fetch(`${API_BASE}/products/${productId}`);
  if (!res.ok) {
    throw new Error(`Không thể tải thông tin sản phẩm #${productId}`);
  }
  return res.json();
}

/**
 * Fetch product approved customer reviews
 */
export async function fetchProductReviews(
  productId: number,
  limit = 5
): Promise<ProductReviewsResponse> {
  const res = await fetch(`${API_BASE}/products/${productId}/reviews?limit=${limit}`);
  if (!res.ok) {
    throw new Error(`Không thể tải đánh giá sản phẩm #${productId}`);
  }
  return res.json();
}

/**
 * Format Currency VND
 */
export function formatVND(amount?: number | null): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return 'Liên hệ';
  }
  return new Intl.NumberFormat('vi-VN').format(amount) + 'đ';
}
