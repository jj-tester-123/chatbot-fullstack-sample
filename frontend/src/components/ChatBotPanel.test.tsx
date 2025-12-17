import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatBotPanel from './ChatBotPanel';
import * as client from '../api/client';

// API 모킹
vi.mock('../api/client', () => ({
  chat: vi.fn(),
}));

describe('ChatBotPanel', () => {
  const mockOnClose = vi.fn();
  const mockProps = {
    productId: 1,
    productName: '테스트 상품',
    onClose: mockOnClose,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('메시지 전송 후 입력 필드에 포커스가 유지되어야 한다', async () => {
    const user = userEvent.setup();

    // API 응답 모킹
    vi.mocked(client.chat).mockResolvedValue({
      answer: '테스트 응답입니다.',
      sources: [],
      engine: 'gemini',
      product_id: 1,
      suggested_questions: [],
    });

    render(<ChatBotPanel {...mockProps} />);

    // 입력 필드 찾기
    const input = screen.getByPlaceholderText('질문을 입력하세요...');

    // 입력 필드에 포커스 주기
    await user.click(input);
    expect(input).toHaveFocus();

    // 메시지 입력
    await user.type(input, '테스트 질문입니다');
    expect(input).toHaveValue('테스트 질문입니다');

    // 전송 버튼 클릭
    const submitButton = screen.getByRole('button', { name: '전송' });
    await user.click(submitButton);

    // 입력 필드가 비워졌는지 확인
    await waitFor(() => {
      expect(input).toHaveValue('');
    });

    // API가 호출되었는지 확인
    await waitFor(() => {
      expect(client.chat).toHaveBeenCalledWith({
        query: '테스트 질문입니다',
        product_id: 1,
        conversation_history: ['테스트 질문입니다'],
      });
    });

    // 응답이 표시되는지 확인
    await waitFor(() => {
      expect(screen.getByText('테스트 응답입니다.')).toBeInTheDocument();
    });

    // 입력 필드에 여전히 포커스가 있는지 확인
    expect(input).toHaveFocus();
  });

  it('메시지 전송 후 바로 다음 메시지를 입력할 수 있어야 한다', async () => {
    const user = userEvent.setup();

    // API 응답 모킹
    vi.mocked(client.chat).mockResolvedValue({
      answer: '첫 번째 응답',
      sources: [],
      engine: 'gemini',
      product_id: 1,
      suggested_questions: [],
    });

    render(<ChatBotPanel {...mockProps} />);

    const input = screen.getByPlaceholderText('질문을 입력하세요...');

    // 첫 번째 메시지 전송
    await user.click(input);
    await user.type(input, '첫 번째 질문');
    const submitButton = screen.getByRole('button', { name: '전송' });
    await user.click(submitButton);

    // 응답 대기
    await waitFor(() => {
      expect(screen.getByText('첫 번째 응답')).toBeInTheDocument();
    });

    // 포커스가 유지되는지 확인
    expect(input).toHaveFocus();

    // API 모킹 변경
    vi.mocked(client.chat).mockResolvedValue({
      answer: '두 번째 응답',
      sources: [],
      engine: 'gemini',
      product_id: 1,
      suggested_questions: [],
    });

    // 두 번째 메시지를 바로 입력할 수 있어야 함 (클릭 없이)
    await user.type(input, '두 번째 질문');
    expect(input).toHaveValue('두 번째 질문');

    await user.click(submitButton);

    // 두 번째 응답 확인
    await waitFor(() => {
      expect(screen.getByText('두 번째 응답')).toBeInTheDocument();
    });

    // 여전히 포커스가 유지되는지 확인
    expect(input).toHaveFocus();
  });
});
