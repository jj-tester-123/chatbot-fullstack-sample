/**
 * 챗봇 레이어 UI
 * - 질문 입력
 * - (엔진 선택 제거: Gemini만 사용)
 * - 응답 표시
 * - 소스 표시
 */
import { useState, useRef, useEffect } from 'react';
import { chat } from '../api/client';
import type { ChatResponse } from '../api/client';
import './ChatBotPanel.css';

interface ChatBotPanelProps {
  productId: number;
  productName: string;
  onClose: () => void;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatResponse['sources'];
}

export default function ChatBotPanel({
  productId,
  productName,
  onClose,
}: ChatBotPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // 로딩이 끝나면 입력 필드에 포커스
  useEffect(() => {
    if (!loading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');

    // 사용자 메시지 추가
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      // API 호출
      const response = await chat({
        query: userMessage,
        product_id: productId,
      });

      // 응답 메시지 추가
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
        },
      ]);
    } catch (error) {
      // 에러 메시지 추가
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `죄송합니다. 오류가 발생했습니다: ${
            error instanceof Error ? error.message : '알 수 없는 오류'
          }`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chatbot-overlay" onClick={onClose}>
      <div className="chatbot-panel" onClick={(e) => e.stopPropagation()}>
        {/* 헤더 */}
        <div className="chatbot-header">
          <div>
            <h2>AI 쇼핑 도우미</h2>
            <p>{productName}</p>
          </div>
          <button className="close-button" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* 엔진 선택 */}
        {/* Gemini만 사용 */}

        {/* 메시지 영역 */}
        <div className="messages-container">
          {messages.length === 0 && (
            <div className="welcome-message">
              <p>안녕하세요! 이 상품에 대해 궁금한 점을 물어보세요.</p>
              <div className="example-questions">
                <p>예시 질문:</p>
                <ul>
                  <li>이 제품의 주요 특징은 무엇인가요?</li>
                  <li>배터리는 얼마나 가나요?</li>
                  <li>방수 기능이 있나요?</li>
                  <li>다른 사용자들의 평가는 어떤가요?</li>
                </ul>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-content">
                {message.content}
              </div>
              
              {/* 소스 표시 (assistant 메시지만) */}
              {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                <div className="message-sources">
                  <details>
                    <summary>참고한 정보 ({message.sources.length}개)</summary>
                    <div className="sources-list">
                      {message.sources.map((source, idx) => (
                        <div key={idx} className="source-item">
                          <span className="source-type">{source.type}</span>
                          <span className="source-score">
                            {(source.score * 100).toFixed(0)}% 관련도
                          </span>
                          <p className="source-content">{source.content}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="message assistant loading">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 입력 영역 */}
        <form className="input-form" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="질문을 입력하세요..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            전송
          </button>
        </form>
      </div>
    </div>
  );
}

