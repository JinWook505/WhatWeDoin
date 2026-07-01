import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import Page from '../src/app/page'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}))

describe('Home Page', () => {
  it('renders the single query input without a station picker', () => {
    render(<Page />)

    const heading = screen.getByRole('heading', {
      name: /오늘 뭐하고 놀지/,
      level: 1,
    })
    expect(heading).toBeInTheDocument()

    expect(screen.getByLabelText(/어떻게 놀고 싶어/)).toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/지하철역 검색/)).not.toBeInTheDocument()
  })
})
