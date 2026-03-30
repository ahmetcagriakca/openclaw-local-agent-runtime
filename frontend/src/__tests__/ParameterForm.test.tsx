import { describe, test, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ParameterForm } from '../components/ParameterForm'
import type { TemplateParameter } from '../types/api'

describe('ParameterForm', () => {
  const stringParam: TemplateParameter = {
    name: 'project_name',
    type: 'string',
    required: true,
    description: 'Project name',
    default: 'my-project',
  }

  const numberParam: TemplateParameter = {
    name: 'max_retries',
    type: 'number',
    required: false,
    description: 'Maximum retries',
    default: 3,
  }

  const booleanParam: TemplateParameter = {
    name: 'verbose',
    type: 'boolean',
    required: false,
    description: 'Enable verbose output',
    default: false,
  }

  const arrayParam: TemplateParameter = {
    name: 'tags',
    type: 'array',
    required: false,
    description: 'Tags',
  }

  test('renders text input for string param', () => {
    render(<ParameterForm parameters={[stringParam]} values={{}} onChange={vi.fn()} />)
    const input = screen.getByLabelText(/Project name/i)
    expect(input).toBeTruthy()
    expect(input.getAttribute('type')).toBe('text')
  })

  test('renders number input for number param', () => {
    render(<ParameterForm parameters={[numberParam]} values={{}} onChange={vi.fn()} />)
    const input = screen.getByLabelText(/Maximum retries/i)
    expect(input).toBeTruthy()
    expect(input.getAttribute('type')).toBe('number')
  })

  test('renders checkbox for boolean param', () => {
    render(<ParameterForm parameters={[booleanParam]} values={{}} onChange={vi.fn()} />)
    const input = screen.getByRole('checkbox')
    expect(input).toBeTruthy()
    expect(input.getAttribute('type')).toBe('checkbox')
  })

  test('shows required indicator for required params', () => {
    render(<ParameterForm parameters={[stringParam]} values={{}} onChange={vi.fn()} />)
    expect(screen.getByText('*')).toBeTruthy()
  })

  test('does not show required indicator for optional params', () => {
    render(<ParameterForm parameters={[numberParam]} values={{}} onChange={vi.fn()} />)
    expect(screen.queryByText('*')).toBeNull()
  })

  test('pre-fills default values for string', () => {
    render(<ParameterForm parameters={[stringParam]} values={{}} onChange={vi.fn()} />)
    const input = screen.getByLabelText(/Project name/i) as HTMLInputElement
    expect(input.value).toBe('my-project')
  })

  test('pre-fills default values for number', () => {
    render(<ParameterForm parameters={[numberParam]} values={{}} onChange={vi.fn()} />)
    const input = screen.getByLabelText(/Maximum retries/i) as HTMLInputElement
    expect(input.value).toBe('3')
  })

  test('calls onChange when user types in text input', () => {
    const onChange = vi.fn()
    render(<ParameterForm parameters={[stringParam]} values={{}} onChange={onChange} />)
    const input = screen.getByLabelText(/Project name/i)
    fireEvent.change(input, { target: { value: 'new-project' } })
    expect(onChange).toHaveBeenCalledWith({ project_name: 'new-project' })
  })

  test('calls onChange when user types in number input', () => {
    const onChange = vi.fn()
    render(<ParameterForm parameters={[numberParam]} values={{}} onChange={onChange} />)
    const input = screen.getByLabelText(/Maximum retries/i)
    fireEvent.change(input, { target: { value: '5' } })
    expect(onChange).toHaveBeenCalledWith({ max_retries: 5 })
  })

  test('calls onChange when user toggles checkbox', () => {
    const onChange = vi.fn()
    render(<ParameterForm parameters={[booleanParam]} values={{}} onChange={onChange} />)
    const input = screen.getByRole('checkbox')
    fireEvent.click(input)
    expect(onChange).toHaveBeenCalledWith({ verbose: true })
  })

  test('shows error messages', () => {
    render(
      <ParameterForm
        parameters={[stringParam]}
        values={{}}
        onChange={vi.fn()}
        errors={{ project_name: 'This field is required' }}
      />,
    )
    expect(screen.getByText('This field is required')).toBeTruthy()
  })

  test('renders text input for array param with placeholder', () => {
    render(<ParameterForm parameters={[arrayParam]} values={{}} onChange={vi.fn()} />)
    const input = screen.getByLabelText(/Tags/i)
    expect(input.getAttribute('placeholder')).toBe('Comma-separated values')
  })

  test('shows empty state when no parameters', () => {
    render(<ParameterForm parameters={[]} values={{}} onChange={vi.fn()} />)
    expect(screen.getByText('This template has no parameters.')).toBeTruthy()
  })
})
