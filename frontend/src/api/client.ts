/**
 * API 클라이언트
 * - 백엔드 API 호출을 위한 fetch 래퍼
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 상품 정보
 */
export interface Product {
  id: number;
  name: string;
  image_url: string;
  price: number;
  category: string;
  description: string;
}

/**
 * 상품 텍스트
 */
export interface ProductText {
  id: number;
  product_id: number;
  type: string; // description, review, qna
  content: string;
}

/**
 * 상품 상세 정보
 */
export interface ProductDetail {
  product: Product;
  texts: ProductText[];
}

/**
 * 챗봇 요청
 */
export interface ChatRequest {
  query: string;
  product_id: number;
  engine: 'gemini' | 'local';
}

/**
 * 컨텍스트 소스
 */
export interface ContextSource {
  content: string;
  type: string;
  score: number;
}

/**
 * 챗봇 응답
 */
export interface ChatResponse {
  answer: string;
  sources: ContextSource[];
  engine: string;
  product_id: number;
}

/**
 * API 에러 처리
 */
class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/**
 * fetch 래퍼
 */
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        errorData.detail || `API 오류: ${response.statusText}`
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new Error(`네트워크 오류: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
  }
}

/**
 * 상품 목록 조회
 */
export async function getProducts(): Promise<Product[]> {
  return fetchApi<Product[]>('/products');
}

/**
 * 상품 상세 조회
 */
export async function getProductDetail(productId: number): Promise<ProductDetail> {
  return fetchApi<ProductDetail>(`/products/${productId}`);
}

/**
 * 챗봇 질의응답
 */
export async function chat(request: ChatRequest): Promise<ChatResponse> {
  return fetchApi<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

