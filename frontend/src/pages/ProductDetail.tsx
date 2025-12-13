/**
 * 상품 상세 페이지
 * - 상품 정보 표시
 * - 챗봇 열기 버튼
 * - 챗봇 레이어 UI
 */
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getProductDetail } from '../api/client';
import type { ProductDetail } from '../api/client';
import ChatBotPanel from '../components/ChatBotPanel';
import './ProductDetail.css';

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    if (id) {
      loadProduct(parseInt(id));
    }
  }, [id]);

  const loadProduct = async (productId: number) => {
    try {
      setLoading(true);
      const data = await getProductDetail(productId);
      setProduct(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '상품 정보를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="product-detail-container">
        <div className="loading">상품 정보를 불러오는 중...</div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="product-detail-container">
        <div className="error">{error || '상품을 찾을 수 없습니다.'}</div>
        <button onClick={() => navigate('/products')}>목록으로 돌아가기</button>
      </div>
    );
  }

  const { product: productInfo, texts } = product;

  // 텍스트 타입별로 그룹화
  const descriptions = texts.filter((t) => t.type === 'description');
  const reviews = texts.filter((t) => t.type === 'review');
  const qnas = texts.filter((t) => t.type === 'qna');

  return (
    <div className="product-detail-container">
      <button className="back-button" onClick={() => navigate('/products')}>
        ← 목록으로
      </button>

      <div className="product-detail-content">
        <div className="product-main">
          <img src={productInfo.image_url} alt={productInfo.name} />
          <div className="product-main-info">
            <span className="product-category">{productInfo.category}</span>
            <h1>{productInfo.name}</h1>
            <div className="product-price">
              {productInfo.price.toLocaleString()}원
            </div>
            <p className="product-description">{productInfo.description}</p>
            
            <button
              className="chat-open-button"
              onClick={() => setChatOpen(true)}
            >
              AI 챗봇에게 물어보기
            </button>
          </div>
        </div>

        {descriptions.length > 0 && (
          <section className="product-section">
            <h2>상세 설명</h2>
            {descriptions.map((text) => (
              <div key={text.id} className="text-content">
                {text.content}
              </div>
            ))}
          </section>
        )}

        {reviews.length > 0 && (
          <section className="product-section">
            <h2>고객 리뷰</h2>
            {reviews.map((text) => (
              <div key={text.id} className="review-card">
                {text.content}
              </div>
            ))}
          </section>
        )}

        {qnas.length > 0 && (
          <section className="product-section">
            <h2>Q&A</h2>
            {qnas.map((text) => (
              <div key={text.id} className="qna-card">
                {text.content}
              </div>
            ))}
          </section>
        )}
      </div>

      {/* 챗봇 레이어 */}
      {chatOpen && (
        <ChatBotPanel
          productId={productInfo.id}
          productName={productInfo.name}
          onClose={() => setChatOpen(false)}
        />
      )}
    </div>
  );
}

