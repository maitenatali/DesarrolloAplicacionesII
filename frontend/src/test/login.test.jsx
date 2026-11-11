import { fireEvent, render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { makeStore } from '../app/store';
import Login from '../pages/Login';

function renderLogin() {
  return render(
    <Provider store={makeStore()}>
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    </Provider>,
  );
}

describe('Login', () => {
  it('valida el email institucional y la contraseña antes de llamar a CORE', () => {
    renderLogin();
    fireEvent.change(screen.getByLabelText('Email institucional'), { target: { value: 'alguien@gmail.com' } });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));
    expect(screen.getByLabelText('Email institucional').closest('.field')).toHaveClass('error');
    expect(screen.getByLabelText('Contraseña').closest('.field')).toHaveClass('error');
  });
});
