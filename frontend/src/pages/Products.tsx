/**
 * 상품 목록 페이지
 * - 모든 상품을 카드 형식으로 표시
 * - 상품 클릭 시 상세 페이지로 이동
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getProducts } from '../api/client';
import type { Product } from '../api/client';
import './Products.css';

export default function Products() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await getProducts();
      setProducts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '상품 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleProductClick = (productId: number) => {
    navigate(`/products/${productId}`);
  };

  if (loading) {
    return (
      <div className="products-container">
        <div className="loading">상품 목록을 불러오는 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="products-container">
        <div className="error">{error}</div>
        <button onClick={loadProducts}>다시 시도</button>
      </div>
    );
  }

  return (
    <div className="products-container">
      <header className="products-header">
        <h1>상품 목록</h1>
        <p>AI 챗봇이 상품에 대한 질문에 답변해드립니다</p>
      </header>

      <div className="products-grid">
        {products.map((product) => (
          <div
            key={product.id}
            className="product-card"
            onClick={() => handleProductClick(product.id)}
          >
            <img src={product.image_url} alt={product.name} />
            <div className="product-info">
              <span className="product-category">{product.category}</span>
              <h3>{product.name}</h3>
              <p className="product-description">{product.description}</p>
              <div className="product-price">
                {product.price.toLocaleString()}원
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

