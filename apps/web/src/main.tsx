import React from 'react';
import ReactDOM from 'react-dom/client';

import { App } from '@/app/App';
import { AppProviders } from '@/app/providers';
import '@/styles/global.css';

const rootElement = document.getElementById('root');

if (rootElement === null) {
  throw new Error('Application root element is missing');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </React.StrictMode>,
);