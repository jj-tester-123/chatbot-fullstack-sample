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

function formatDate(value: string) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString();
}

function renderStars(rating?: number | null) {
  const safe = typeof rating === 'number' ? Math.max(0, Math.min(5, rating)) : 0;
  return '★'.repeat(safe) + '☆'.repeat(5 - safe);
}

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatAttention, setChatAttention] = useState(true);
  const [showAllReviews, setShowAllReviews] = useState(false);
  const [showAllQnas, setShowAllQnas] = useState(false);

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

  const { product: productInfo, reviews, qnas } = product;
  const sortedReviews = [...reviews].sort((a, b) => b.id - a.id);
  const sortedQnas = [...qnas].sort((a, b) => b.id - a.id);
  const visibleReviews = showAllReviews ? sortedReviews : sortedReviews.slice(0, 5);
  const visibleQnas = showAllQnas ? sortedQnas : sortedQnas.slice(0, 5);

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

            {/* 쇼핑몰형 버튼 배치 (동작은 추후 연결) */}
            <div className="purchase-actions" role="group" aria-label="구매 관련 버튼">
              <button type="button" className="action-button secondary">
                찜
              </button>
              <button type="button" className="action-button secondary">
                장바구니
              </button>
              <button type="button" className="action-button primary">
                바로구매
              </button>
            </div>
          </div>
        </div>

        <section className="product-section">
          <div className="section-header">
            <h2>상품 정보</h2>
          </div>
          <div className="product-spec-grid">
            <div className="spec-item">
              <span className="spec-label">카테고리</span>
              <span className="spec-value">{productInfo.category || '-'}</span>
            </div>
            <div className="spec-item">
              <span className="spec-label">상품번호</span>
              <span className="spec-value">{productInfo.id}</span>
            </div>
            <div className="spec-item">
              <span className="spec-label">가격</span>
              <span className="spec-value">{productInfo.price.toLocaleString()}원</span>
            </div>
          </div>
        </section>

        <section className="product-section">
          <div className="section-header">
            <h2>상세 설명</h2>
          </div>
          <div className="text-content">{productInfo.description}</div>
        </section>

        <section className="product-section">
          <div className="section-header">
            <h2>고객 리뷰</h2>
            {sortedReviews.length > 5 && (
              <button
                type="button"
                className="section-action"
                onClick={() => setShowAllReviews((v) => !v)}
              >
                {showAllReviews ? '접기' : `더보기 (+${sortedReviews.length - 5})`}
              </button>
            )}
          </div>

          {sortedReviews.length === 0 ? (
            <div className="empty-state">아직 리뷰가 없습니다.</div>
          ) : (
            <div className="card-list">
              {visibleReviews.map((r) => (
                <div key={r.id} className="review-card">
                  <div className="card-meta">
                    <span className="stars" aria-label={`별점 ${r.rating ?? 0}점`}>
                      {renderStars(r.rating)}
                    </span>
                    <span className="meta-sep">·</span>
                    <span className="meta-text">{r.user_name || '익명'}</span>
                    <span className="meta-sep">·</span>
                    <span className="meta-text">{formatDate(r.created_at)}</span>
                  </div>
                  <div className="card-body">{r.review_text}</div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="product-section">
          <div className="section-header">
            <h2>Q&amp;A</h2>
            {sortedQnas.length > 5 && (
              <button
                type="button"
                className="section-action"
                onClick={() => setShowAllQnas((v) => !v)}
              >
                {showAllQnas ? '접기' : `더보기 (+${sortedQnas.length - 5})`}
              </button>
            )}
          </div>

          {sortedQnas.length === 0 ? (
            <div className="empty-state">아직 등록된 Q&amp;A가 없습니다.</div>
          ) : (
            <div className="card-list">
              {visibleQnas.map((q) => (
                <div key={q.id} className="qna-card">
                  <div className="card-meta">
                    <span className="badge">Q</span>
                    <span className="meta-text">{formatDate(q.created_at)}</span>
                  </div>
                  <div className="card-body qna-question">{q.question}</div>
                  <div className="qna-answer">
                    <span className="badge answer">A</span>
                    <div className="card-body">{q.answer}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* 챗봇 레이어 */}
      {chatOpen && (
        <ChatBotPanel
          productId={productInfo.id}
          productName={productInfo.name}
          onClose={() => setChatOpen(false)}
        />
      )}

      {/* 우측 하단 플로팅 챗봇 버튼 */}
      <button
        type="button"
        className={`floating-chat-button ${chatAttention ? 'attention' : ''}`}
        onClick={() => {
          setChatAttention(false);
          setChatOpen(true);
        }}
        aria-label="AI 챗봇 열기"
      >
        <span className="chat-fab-icon" aria-hidden="true">
          ?
        </span>
        <span className="chat-fab-label">챗봇 문의</span>
      </button>
    </div>
  );
}

