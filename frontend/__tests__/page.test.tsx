import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import Page from '../src/app/page'

describe('Home Page', () => {
  it('renders the WhatWeDoin heading', () => {
    render(<Page />)

    const heading = screen.getByRole('heading', {
      name: /WhatWeDoin/i,
      level: 1,
    })

    expect(heading).toBeInTheDocument()
  })
})
