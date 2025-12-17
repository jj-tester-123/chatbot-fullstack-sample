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
  suggestedQuestions?: string[];
}

export default function ChatBotPanel({
  productId,
  productName,
  onClose,
}: ChatBotPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [askedQuestions, setAskedQuestions] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // 로딩이 끝나면 입력 필드에 포커스
  useEffect(() => {
    if (!loading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [loading]);

  const submitQuestion = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMessage = question.trim();

    // 히스토리에 추가
    setAskedQuestions((prev) => [...prev, userMessage]);

    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await chat({
        query: userMessage,
        product_id: productId,
        conversation_history: askedQuestions,
      });

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          suggestedQuestions: response.suggested_questions,
        },
      ]);
    } catch (error) {
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');

    await submitQuestion(userMessage);
  };

  const handleQuickQuestion = async (question: string) => {
    setInput('');
    await submitQuestion(question);
  };

  const quickQuestions = (() => {
    const base = `${productName} 핵심 특징을 알려줘`;

    if (productName.includes('이불')) {
      return [base, `${productName} 세탁 방법을 알려줘`];
    }

    if (productName.includes('쌀국수')) {
      return [base, `${productName} 소비기한이 어떻게 되나요?`];
    }

    return [base, `${productName} 배송/교환은 어떻게 되나요?`];
  })();

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

        <div className="messages-container">
          {messages.length === 0 && (
            <div className="welcome-message">
              <p>안녕하세요! 이 상품에 대해 궁금한 점을 물어보세요.</p>
              <div className="quick-questions">
                <div className="quick-questions-header">
                  바로 알아보기
                </div>
                <div className="quick-questions-buttons">
                  {quickQuestions.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => handleQuickQuestion(q)}
                      disabled={loading}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
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

              {/* 추천 질문 표시 */}
              {message.role === 'assistant' &&
               message.suggestedQuestions &&
               message.suggestedQuestions.length > 0 && (
                <div className="suggested-questions">
                  <div className="suggested-questions-header">
                    관련 질문
                  </div>
                  <div className="suggested-questions-buttons">
                    {message.suggestedQuestions.map((q, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleQuickQuestion(q)}
                        disabled={loading}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
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
