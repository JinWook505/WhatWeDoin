import '@testing-library/jest-dom'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ClarificationStep from '../src/components/ClarificationStep'
import { recommend } from '../src/lib/api'

jest.mock('../src/lib/api', () => {
  const actual = jest.requireActual('../src/lib/api')
  return {
    ...actual,
    recommend: jest.fn(),
  }
})

const mockRecommend = recommend as jest.Mock

describe('ClarificationStep', () => {
  beforeEach(() => {
    mockRecommend.mockReset()
  })

  it('forwards the already-resolved station_name on resubmit when station search is not shown', async () => {
    mockRecommend.mockResolvedValue({
      success: true,
      data: { course_id: 1, title: '', description: '', station_name: null, theme_tags: [], stages: [], similar_top_courses: [], served_from: 'LLM' },
      error: null,
    })

    render(
      <ClarificationStep
        query="혼자 인천공항 근처에서 밥먹고싶은데 추천좀 해줘"
        missingFields={['budget_tier']}
        partialParsedInput={{
          theme_tags: ['FOOD'],
          head_count: 1,
          station_name: '인천공항1터미널',
        }}
      />,
    )

    expect(screen.queryByLabelText(/어느 역 근처에서/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '~3만원' }))
    fireEvent.click(screen.getByRole('button', { name: '코스 만들기' }))

    await waitFor(() => expect(mockRecommend).toHaveBeenCalled())

    const [, , , resolved] = mockRecommend.mock.calls[0]
    expect(resolved.parsedInput.station_name).toBe('인천공항1터미널')
  })
})
