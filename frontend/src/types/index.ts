/**
 * LifeGift Type Definitions
 */

export interface ProductCard {
  id: number;
  name: string;
  price: number;
  sale_price: number | null;
  effective_price: number;
  origin: string | null;
  available_quantity: number;
  is_available: boolean;
  image_url: string | null;
  reason?: string | null;
  weight?: number | null;
  price_per_kg?: number | null;
  price_basis?: string | null;
  category_name?: string | null;
}

export interface Certificate {
  name: string;
  certificate_code?: string;
  issuer?: string;
  issue_date?: string;
  expiry_date?: string;
  issued_at?: string;
  expires_at?: string;
}

export interface ProductDetailResponse {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  category_id?: number | null;
  category_name?: string | null;
  brand_id?: number | null;
  brand_name?: string | null;
  price: number;
  sale_price?: number | null;
  effective_price: number;
  origin?: string | null;
  image_url?: string | null;
  available_quantity: number;
  is_available: boolean;
  ingredients?: string | null;
  taste_profile?: string | null;
  key_benefits?: string | null;
  suitable_for?: string | null;
  usage_instructions?: string | null;
  storage_instructions?: string | null;
  shelf_life?: string | null;
  producer_name?: string | null;
  production_area?: string | null;
  product_story?: string | null;
  extra_attributes?: Record<string, unknown> | null;
  certificates: Certificate[];
}

export interface ReviewItem {
  id: number;
  user_name: string;
  rating: number;
  comment: string;
  is_verified_purchase: boolean;
  created_at: string;
}

export interface ProductReviewsResponse {
  product_id: number;
  average_rating: number;
  total_reviews: number;
  reviews: ReviewItem[];
}

export interface ChatResponse {
  session_id: number;
  intent: string;
  answer: string;
  products: ProductCard[];
  metadata?: Record<string, unknown> | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  products?: ProductCard[];
  intent?: string;
  isError?: boolean;
}

export interface UserAccount {
  id: string;
  name: string;
  roleDescription: string;
  sampleOrder?: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  environment: string;
}
